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

## Tools in the model port (the first slice of ADR 0008)

A `ModelRequest` can offer `tools` (a `ToolDefinition`: a name, a description and a JSON schema) and carry a
`transcript` of earlier rounds (`ModelTurn`: what the model said, the `ToolCall`s it made and the `ToolResult`
of each). A `ModelResponse` can come back with `calls` and the stop reason `tool_use`, which goes with calls
and only with them. Each adapter speaks its provider's format: `tool_use` and `tool_result` content blocks
for Anthropic, `tool_calls` and `role: tool` messages for OpenAI-compatible servers. Some local servers
report `stop` next to a tool call; that is read as `tool_use`. A tool call nobody offered, a malformed
call, or `tool_use` with no call is refused as an unexpected reply.

An adapter never runs a tool. It returns what the model asked for.

**Nothing offers tools yet.** `CallModel` refuses a request that has tools or a transcript, because it
journals text, and a tool turn has to be journaled whole so a resumed run replays it. The tool loop, that
journal and the per-stage allowlist are the next slices. Neither adapter has been run against a live
provider with tools.
