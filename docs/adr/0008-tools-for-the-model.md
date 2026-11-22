# ADR 0008: The model gets tools, each stage gets only the ones it names

Status: proposed

## Context

Until now a model call returns text and nothing else (ADR 0007), and the threat model counts
that as a defence: a successful prompt injection can change what a chapter says, but it cannot
read a file, call a service or spend money outside the run.

The maintainer has decided that the model should have tools, and that web search in particular
should be a tool the model calls rather than a fixed step. The scope given was web search and page
fetch, an outbound MCP client, skills, plugins and marketplaces, with two conditions: a stage may
use only the tools declared for it, and anything third-party runs only if it is pinned and
hash-locked.

That changes a security rule, the shape of the journal that makes a resumed run free, and what
the project can freeze for 1.0. It deserves a reviewed design before code.

## Decision

1. **Tool use is part of the model port, and adapters never run tools.** `ModelRequest` carries
   tool definitions (a name, a description and a JSON schema). `ModelResponse` can carry tool calls
   and a new stop reason, `tool_use`. Each adapter maps these onto its provider's format (content
   blocks for Anthropic, `tool_calls` and `role: tool` for OpenAI-compatible servers). An adapter
   still returns what the model said and nothing more, so the exception type stays the contract.

2. **A bounded loop runs the tools.** A service (`RunToolLoop`) sits above `AskModel`. It caps
   model turns, tool calls, the time of each call, the size of each result and the run's spend (every
   turn reserves against the `SpendGuard`). It runs a call through a `ToolRunner` port and feeds the
   result back. A loop that hits a limit ends with a blocking issue and the stage stops, as an
   incomplete answer does today.

3. **A tool turn is journaled whole.** Every model call keeps its journal entry. Every tool call is
   journaled too: the tool, a canonical hash of its arguments and its result. A resumed run replays
   the stored result for nothing and gets the same bytes, instead of searching again against a web
   that has moved. The key of each later model call includes a hash of the transcript so far, so a
   replay is only ever of the same conversation. This also closes the double-journaling cost gap
   noted in M5, which matters more once calls come in loops.

4. **Each stage declares its tools; none by default.** A `StageRecipe` lists the tools its stage may
   use. Only those are offered to the model and only those can run. A call to anything else is
   answered with "no such tool" and still counts against the call limit. Research gets
   `web_search` and `fetch_url`; drafting gets none. No tool is ever discovered at run time.
   No stage asks a person for permission: the allowlist is the permission, and it is part of the code
   and config a person reviews.

5. **Whatever a tool returns is untrusted text.** A result is fed back inside an `<untrusted>` block
   under a system prompt that says so, is size-capped, and cannot close its own block. Fetched
   pages go through `HtmlTextExtractor`. A `fetch_url` result is also recorded as a `SourceRecord`
   (address, title, hash of the text), which is what claim verification later checks against.

6. **The native tools are thin wrappers.** `web_search` wraps `SearchProviderInterface` (Brave
   first) and returns links and titles only. `fetch_url` wraps `SourceFetcherInterface`, so it
   inherits the URL policy at every redirect, the size and encoding limits and the hidden-text
   stripping. Their keys come from the secret provider by name and never reach the model or a log.

7. **MCP is an outbound client, with servers you list.** A server is declared in a lock file with
   a pinned command or address and version, and with a hash of the tool definitions it advertised
   when it was added. If a server later advertises different tools or descriptions (tool poisoning, or
   a changed server), the run refuses to start. Servers are reached over stdio, in a subprocess with
   an allow-list environment and the same time, memory and disk limits as the build tools, or over
   HTTP to an address the URL policy accepts, with no redirects. A server's tool is offered to a stage
   only if the stage names it (`server.tool`).

8. **Skills are versioned prompt packs, never code and never tools.** A skill adds named prompt
   parts, in the same TOML shape and with the same version lock as `PromptTemplate`. Loading one
   cannot add a tool, run a command or widen a stage's allowlist.

9. **Plugins and marketplaces are install-time, human-driven, and pinned.** A plugin is a bundle
   of MCP server definitions and skills. A marketplace is only an index of such bundles, with an
   address and a hash for each. A person runs `ei tools add` to copy an entry into the lock file,
   which records the pinned version and the SHA-256 of the bundle; the change is reviewed like any
   other commit. Nothing updates itself, and a run never contacts a marketplace. This is how the
   request for marketplaces fits the condition that third-party code must be pinned and hash-locked:
   a marketplace is where a person finds something to pin, not a source a run trusts.

10. **ACP is not a tool source.** The Agent Client Protocol lets an editor or client drive this
    agent. It is the inbound surface already planned for M8, with its own consent rules for spend. It
    gives the model no tools and is built separately.

## Consequences

- The threat model's "the model has no tools" is replaced by decisions 2, 4 and 5, and the
  document is updated as each lands. Until a tool exists the model has none.
- A prompt injection in a search result or page can now try to make the model call a tool. The
  defences are the per-stage allowlist (a drafting stage has nothing to call), the loop's limits,
  the spend reservation, the untrusted wrapping, and the fact that the native tools can only read
  public pages through the URL policy. An MCP server widens this and is the reason it is pinned,
  hash-locked, resource-limited and named per stage.
- The journal format changes (decision 3). Existing journal rows stay readable; a run started
  before the change replays as before.
- 1.0 freezes less if less ships: the tool-lock file format, the tool schema the model sees and the
  `ei tools` commands become contracts once released. Skills, plugins and marketplaces are the
  parts most likely to want change, so they land last and may ship as experimental.
- Two costs: a model call that reaches for a tool takes more turns than one that does not, and a
  stage with tools is harder to reproduce exactly than one without, which is what the journal
  replay is for.

## Slices

1. Tool use in the model port and both adapters, with cassettes for tool turns.
2. `RunToolLoop`, the tool journal and replay, the `ToolRunner` port and the per-stage allowlist.
3. `web_search` and `fetch_url` as tools; the research stage uses them.
4. The tool lock file and `ei tools add`; the MCP client over stdio, then HTTP.
5. Skills as prompt packs.
6. Plugins and marketplace indexes, install-time only.

## Open questions

- How strong a sandbox a stdio MCP server needs beyond the environment allow-list and resource
  limits, on macOS and on Linux.
- Whether a tool may carry its own secret, and how that is named in the lock file without the
  value ever being in it.
- Whether a stage's tool allowlist lives with its recipe in code or in the lock file, or both with
  the lock file able to narrow but never widen the code's list. This ADR leans to the last.

## Amendments from slice 4

Recorded on 2026-11-22 while building slice 4 ([TOOL_LOCK.md](../TOOL_LOCK.md)).

- **What the lock pins (decision 7).** The maintainer chose to hash the files, not only the tool
  definitions: the lock records the SHA-256 of a stdio server's executable and of every script among its
  arguments, plus the server's reported name and version and a hash of the tools it advertises. A
  launcher that fetches code on each run (`npx`, `uvx`, `docker` and the like) is refused, because what
  it would run cannot be hashed. Installed dependencies are not covered, and this is stated rather than
  hidden.
- **Names.** A tool from a server is offered to the model as `<server>__<tool>`, because the providers
  accept only letters, digits, `-` and `_`; recipes and the lock use the same form, not `server.tool`.
- **A tool's secret (open question 2).** The lock names the environment variables a server is given,
  never their values. Values come from the environment at start.
- **Slicing.** Slice 4 is built as 4a (lock models, file format, MCP client over an abstract transport,
  verifier), 4b (a stdio transport under the build tools' limits, and `ei tools`), 4c (wiring the registry
  and the start-up check) and 4d (HTTP).
