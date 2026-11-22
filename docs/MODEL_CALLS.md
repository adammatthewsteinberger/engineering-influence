# Asking a model

A stage never talks to a provider directly. It goes through two services, one above the other.

## `CallModel`: one call, at most once

1. A request already answered **in this run and stage** is replayed from the run journal for nothing.
2. Otherwise the worst-case cost is reserved from the run's `SpendGuard` before anything is sent. A
   call that does not fit raises `BudgetExceededError` having sent nothing.
3. The call is made. If it raises, the reservation is released and nothing is journaled.
4. The answer is journaled with its real cost before the reservation is settled.

A replay is always a *complete* answer. A cut-off or declined answer is journaled too, because it was
billed, but under a key that includes the outcome and the attempt, so it is never mistaken for a good one.

## `AskModel`: what to do when the answer is not complete

A stage calls `AskModel.ask(guard, run_id, stage, attempt, request)` and gets a `ModelAnswer`: the text,
whether it is `complete`, the `issues` if it is not, and what it cost.

| What happened | What `AskModel` does |
|---|---|
| The model finished | Returns the answer. |
| It hit its output cap | Asks again with the cap **doubled**, up to the model's own limit. At the limit there is nothing more to try. |
| It declined | Asks the **identical** request again, up to `refusal_retries` times (default 1). |
| It runs out of attempts (default 4 calls in all) | Returns the best text it has and one **blocking** `QualityIssue` per defect: `TRUNCATED` (the text ends part-way) and/or `REFUSED` (the model's own words, trimmed to one line of 300 characters). The stage carries on. |
| The run is out of money, or the provider is down or at capacity | Nothing is caught here. `BudgetExceededError`, `TransientStageError` and `CapacityExhaustedError` go to the run, which retries or parks it. |

- **A refusal is never reworded, pressed or disguised.** It is the model's decision; a retry only covers a
  refusal that was a fluke. If it keeps declining, the stage gets no text and a `REFUSED` issue, and decides
  what to do (a later stage can step down a `DegradeLadder`, or the run records the section as missing).
- **Both issues are blocking**, so `--strict-release` refuses a book with a cut-off or missing section.
  An autonomous run still finishes and says what is wrong.
- **A resumed run does not pay twice.** Before any live call, `AskModel` looks for a complete answer at
  every output cap it could have reached, so a run that already has its answer replays it for nothing,
  without re-paying the cut-off attempts that led to it. An incomplete answer is never replayed: a resume
  tries again.
- **Every call is counted.** Each live call is journaled under `attempt * max_attempts + i`, so a stage's own
  retries and these attempts never share a journal key and no cost is lost.
- The issue detail quotes the model's own words, so treat it as untrusted text wherever it is shown.

## Tools in the model port (slices 1 and 2 of ADR 0008)

A `ModelRequest` can offer `tools` (a `ToolDefinition`: a name, a description and a JSON schema) and carry a
`transcript` of earlier rounds (`ModelTurn`: what the model said, the `ToolCall`s it made and the `ToolResult`
of each). A `ModelResponse` can come back with `calls` and the stop reason `tool_use`, which goes with calls
and only with them. Each adapter speaks its provider's format: `tool_use` and `tool_result` content blocks
for Anthropic, `tool_calls` and `role: tool` messages for OpenAI-compatible servers. Some local servers
report `stop` next to a tool call; that is read as `tool_use`. A tool call nobody offered, a malformed
call, or `tool_use` with no call is refused as an unexpected reply.

An adapter never runs a tool. It returns what the model asked for.

### The tool loop

`RunToolLoop` sits above `AskModel` and is how every model-backed stage is run; a stage with no tools is a
loop of one turn. Each turn is one `AskModel` call, so a cut-off or declined answer, a replay and the spend
cap work as they do without tools. When the model answers with tool calls, each is run through the
`ToolRunner` and the round (what the model said, what it called, what came back) is added to the transcript
the next request carries.

- **Only the tools a stage names exist for it.** A `StageRecipe` lists its tools (none by default). The
  executor offers exactly those, and the runner runs only those. A call to any other name, registered or
  not, is answered with `no tool named '…' is available here` and nothing runs. A recipe that names a tool
  nobody registered stops the stage before anything is asked (`STAGE_TOOL_UNKNOWN`).
- **Arguments are checked first** against the tool's schema (`required`, each property's `type` and `enum`,
  and `additionalProperties: false`). A bad call is answered with what is wrong and nothing runs.
- **A tool call is made once.** Its result is journaled by tool and canonical arguments, per run and stage,
  at no cost. A resumed run, a retry, or a model that asks the same thing twice gets the stored result and
  the web is not asked again. A failure the model can work around (`ApplicationError`) is stored as an error
  result; a transient or capacity failure is not stored and goes up to the run.
- **A model turn is journaled whole.** A request with tools is keyed by the tools offered and by the whole
  transcript so far (every call's id, name and arguments, every result and its error flag), and its answer
  is stored as the text and the calls together. A `tool_use` and an `end_turn` both replay. A request with
  no tools is keyed and stored exactly as before, so existing journals still replay. A run that stopped in
  the middle of a conversation replays the finished turns and calls and goes on from the first unfinished
  one.
- **It is bounded.** `ToolLoopLimits` caps turns (8), tool calls (16), the characters of a result (20,000,
  cut with a note of how many were dropped) and the seconds of a call (60). Past the turn cap the loop ends
  with a blocking `TOOL_LOOP_EXHAUSTED` issue and the stage stops. A call past the call cap is not run; its
  result tells the model to answer with what it has. Every turn reserves against the `SpendGuard`.
- **A call that outlives its deadline is a transient failure.** The tool's thread cannot be killed, so a
  tool should bound itself too; the runner's pool is small (4), so a tool that never returns fills it and
  later calls time out.

- **Whatever a tool says is untrusted.** `ToolRunner` wraps a tool's text, and the text of an error it
  raises, in an `<untrusted name="tool:...">` block, after cutting it to the limit and before it is stored,
  so a replay shows the model the same wrapped text. A copy of the tag inside the text is defused, so a
  page cannot close the block and speak outside it. The runner's own refusals are ours and are not wrapped.
  The research prompt tells the model that everything a tool returns is evidence, never instructions.

### The tools that exist

The runtime registers `web_search` and `fetch_url` (model-backed runs only), and only the research stage
names them. A run given a tool lock (`EI_TOOL_LOCK`) also registers the tools of each locked MCP server as
`<server>__<tool>`, and a stage is offered one only if the lock grants it that stage ([TOOL_LOCK.md](TOOL_LOCK.md#in-a-run)).

- **`web_search`** lists titles and links, best first, with no page text (a hit carries no snippet), so
  nothing is quoted until it has been read. The provider is SearXNG, with Brave behind it when both are
  configured (see [CONFIGURATION.md](CONFIGURATION.md)).
- **`fetch_url`** reads one page through the source fetcher, which only reads public https, checks every
  redirect, limits size and encoding, and drops hidden text. It only reads an address the model was shown,
  copied exactly: one in the stage's prompt, a link line of an earlier successful search, or the `Source:`
  header of an earlier successful fetch. A tool can refuse a call by what the model has seen
  (`ToolInterface.refuses`) and says what counts as shown (`ToolInterface.shown`, nothing by default); the
  runner builds the evidence from the prompt and those parts of successful results only, never from an
  error message or page text, and checks it before the journal, so a refusal is never stored. This stops a
  hostile page steering the model to an address with the brief in it. It returns the final address, the title, a
  SHA-256 of the text and the text. That header is the pin a later claim check will use; the journal keeps
  it, but it is not yet stored as a separate source record.

Neither the model nor either adapter has been run against a live provider, search service or website.
