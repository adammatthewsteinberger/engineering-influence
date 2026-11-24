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

Recorded on 2026-11-22 while building slice 4 ([TOOL_LOCK.md](../tool-lock.md)).

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
- **Running a server (4b).** A stdio server runs in its own process group with a bare environment and a
  throwaway home, under time, memory and disk limits, and is stopped by killing the group before the leader
  is reaped. It is not sandboxed. `ei tools add` runs the server, so it refuses a launcher, a missing
  executable or a relative script before starting anything, and `ei tools verify` never starts a server
  whose files have changed.
- **Where a stage's permission for a locked tool lives (4c; the third open question).** In the lock file,
  chosen by the maintainer: a per-server `[server.grants]` table naming, for each stage, exactly which of the
  server's tools it may call, with no wildcards. Recipes in code still name the built-in tools; the stage's
  offered tools are the recipe's plus the lock's grants. It is reviewed in the same commit as the server.
- **A run reads a lock only when `EI_TOOL_LOCK` names it**, so a stray file in the working directory starts no
  server, and a tool's journal key includes the tool's revision (for a locked tool, the hash of the server's
  tools) so a replaced server's old answers are not replayed.
- **Remote servers (4d).** HTTP follows decision 7 and the slices above, with these choices. The transport is
  Streamable HTTP, one POST per message, the answer as JSON or as events read within the same request, and no
  stream of the client's own. A remote entry locks the **address** and what the server advertises; its code
  cannot be hashed, and the weaker pin is stated in the docs and the `ei tools add` output rather than
  hidden. The address goes through the existing public-https URL policy before every request, with no
  redirects, so **a server on this machine or network is reached over stdio, not HTTP**; a loosening for
  local development is a separate decision. Credentials are a named variable (`bearer_env`), never part of
  the address, and the lock refuses a user, query or fragment so a secret cannot be committed in a URL.
  Other auth schemes (OAuth, custom headers) are not built.
- **Outbound connections are pinned to the checked address (after 4d).** A security review of the remote
  transport found what the docs had listed as a gap: the policy resolved a name when asked and the client
  resolved it again when it connected. `PublicHttpsUrlPinner` now resolves once, has the policy judge every
  address, and hands the caller the vetted address with the name for the `Host` header and for TLS, so the
  certificate is still checked against the name. `fetch_url` and the remote transport use it; only one
  address is tried, and `fetch_url` sends `Connection: close` so a connection verified for one name is not
  reused for another that shares its address. Signed webhook delivery was not changed.

## Amendments from slice 5

Recorded on 2026-11-22 while building slice 5 ([SKILLS.md](../skills.md)).

- **A skill is one file of text, with a part for each stage it speaks to (decision 8).** The ADR said "named
  prompt parts, in the same TOML shape as `PromptTemplate`". A template's parts are the pieces of one prompt
  (`system`, `user`) with blanks to fill; a skill's parts are *which stage the text is for*. A skill has no
  blanks, so there is nothing to fill and no value to smuggle into; it has no `untrusted` list, because all of
  it is text a person chose; and any key it should not have (`command`, `tools`, `url`) is refused by name.
- **The version lock is a hash, in its own lock file.** A shipped template is pinned by a fingerprint in a test
  fixture. A skill is installed by a person, so it is pinned by the SHA-256 of its file's bytes in
  `ei-skills.lock.toml`, which a run reads only when `EI_SKILL_LOCK` names it. It is a separate file from the tool
  lock so either can be used alone; plugins (slice 6) will copy entries into both. `ei skills add` keeps a copy
  of the file in a `skills/` folder beside the lock, so what is committed is what is hashed, and the lock
  needs no paths.
- **Permission is per stage and explicit, as for tools.** A new skill is enabled for no stage. `ei skills
  enable NAME STAGE` checks the file against its hash and refuses a stage the skill has no text for; at most four
  skills may be enabled for one stage; locking a skill again clears its stages, because new text has not been
  approved for anything.
- **Where the text goes (a decision the ADR left open).** At the end of the **user** part of the stage's prompt, in
  a delimited block under a fixed frame (the `skill_guidance` template), never in the system part. It is not
  wrapped as `<untrusted>`: unlike a page, it is meant to instruct, and the person approved it. The trade-off
  is stated plainly in [SKILLS.md](../skills.md#what-this-does-and-does-not-give-you): **a skill that was hostile
  when it was locked is trusted as locked.** A copy of the block's tags inside a skill is defused.
- **What a person approved is what a model sees.** Text that renders as nothing or reorders what is shown
  (control characters, zero-width and bidirectional marks, line and paragraph separators, private-use and
  unassigned code points) is refused when the skill is read, and each part is capped, so a skill cannot hide an
  instruction from the review the lock exists for.
- **The journal key (decision 3) names the skills.** A stage with skills sends
  `<template>@<n>+skill_guidance@<n>:<digest>`, the digest covering each skill's name, version and hash, so a
  resumed run replays an answer only for the same text. A stage with no skill enabled sends exactly the prompt
  and version it always did, so existing journals are unaffected.
- **The check happens once, at start, before anything else.** Skills enabled for some stage are read and
  hashed when the stage executor is built, before any tool server is started or any model is called; the text
  is then held for the life of the process, so every stage of a run sees the same text. A skill that is
  installed but enabled for no stage is not read.
- **What a skill still cannot do.** It adds no tool, changes no stage's allowlist, output cap or system
  prompt, and cannot raise a budget: those are decided in code, in the tool lock and in the spend guard.

## Amendments from slice 6a

Recorded on 2026-11-22 while building the first part of slice 6 ([PLUGINS.md](../plugins.md)). Slice 6 is split as
slice 4 was: **6a** plugins installed from a file on disk, **6b** marketplace indexes and fetching.

- **Installing a plugin runs and contacts nothing (decision 9).** The ADR said a person runs `ei tools add` to copy
  an entry into the lock. The installer therefore does not run a bundle's servers: a bundle is text from someone
  else, and `ei tools add` is the step that starts a server (or contacts one) and pins what it reports. The
  installer locks the bundle's **skills** (each enabled for no stage) and **prints** the exact `ei tools add`
  command for each server, shell-quoted, for a person to review and run.
- **A bundle cannot decide what a model may do.** There is no key for a grant, for a stage to enable a skill for,
  or for anything else; any unknown key is refused. A server definition is held to the same rules the tool lock
  uses (an absolute command that is not a launcher, an https address with no secret in it), so a plugin cannot
  describe a server the lock would refuse.
- **One file, one hash.** A plugin is a single TOML file with `[[server]]` and `[[skill]]` tables, so one SHA-256
  pins everything a person reviewed. Skills in it are read by the same strict parser as a skill file, and are
  written into the skill lock as skill files, so they are ordinary skills afterwards.
- **A third lock file, which a run never reads.** `ei-plugins.lock.toml` records the bundle's hash, the servers it
  described and the hash each skill was locked under, so `ei plugins verify` can check the bundle that was
  reviewed and `ei plugins remove` can undo the install. What a run may do stays in the tool lock and the skill
  lock; no new thing is added to the run's trust surface.
- **No replace.** A plugin that is installed, or whose skills are already locked, is refused before anything is
  written. Installing a newer version is `remove` then `add`, because replacing text a person approved is a
  decision, not a side effect. `remove` deletes only skills that are still exactly what the plugin installed.
- **An install either completes or leaves nothing.** The bundle's copy is written first, and a failure while locking
  a later skill removes the copy and the skills already locked.

## Amendments from slice 6b

Recorded on 2026-11-22 while building the second part of slice 6 ([PLUGINS.md](../plugins.md#marketplace-indexes)).

- **A marketplace is only an index, and a download is a separate step from an install (decision 9).** An index is a
  TOML file of plugin names, versions, descriptions, addresses and SHA-256 hashes, with no other key. `ei plugins
  fetch INDEX NAME` downloads one plugin file, checks its hash against the index's **before reading it as
  anything**, checks that it is the plugin and version the index named, and saves it; it installs nothing. A
  person reads it with `ei plugins show` and installs it with `ei plugins add`, which stays an offline step on a
  local file. This keeps the one network-facing command narrow: it can produce a file, and cannot change a lock.
- **A run never contacts a marketplace.** Only `search` and `fetch`, run by a person, can use a network, and
  `add`, `show`, `verify` and `remove` never do.
- **The download is held to the rules every other outbound connection here is.** It goes through the same
  pinned-address URL policy as `fetch_url` and the remote tool transport (https, a public address checked each
  time, the connection made to the address that was checked with the name in TLS), follows no redirect, sends no
  cookie or credential, accepts no compression and is bounded to 512 KiB and 30 seconds. An address in an index
  is held to the lock's rules for a remote server (no user, password, query string or fragment).
- **An index is not trusted more than its host.** Indexes and plugin files are not signed, so the hash only proves
  that the bytes are the ones the index described. Vouching for a publisher (signatures, a key to trust) is a
  decision this slice does not make; the defence is that a person reads the file and that installing enables
  nothing.
- **The core install still works without `httpx`.** The downloader is built on first use, and a missing dependency
  becomes a message that names the `runtime` extra; a local index file needs no network code at all.

## Amendments from M6.5: `SKILL.md` import and reference sections (2026-11-22)

- **A skill may carry reference sections** (`[reference]`, `"title" = "text"`), read on request. This is the one place a skill
  changes what a stage is offered, and it adds exactly one built-in, read-only tool: `read_skill`. It is offered to a stage only
  when a reference skill is enabled for that stage, and the guidance says so (`Guidance.tools`), so the prompt never points at
  a tool the model was not given. It can return the text of a section of a skill the lock approved, hash-checked at start, and nothing else:
  no file, no address, no other state.
- **The stage's prompt is the permission.** The tool is shared, so each call is checked against what the stage's own prompt lists,
  through the same `refuses` hook `fetch_url` uses. A skill enabled for one stage cannot be read from another. A section's text is
  returned as the tool's result, which the runner wraps as untrusted, and a section is never longer than the runner's result limit, so it is never cut.
  A stored result carries a digest of every reference section as its revision, so a changed skill is not answered from an old result.
- **Skills from the wild:** `ei skills import` reads a `SKILL.md` (frontmatter `name` and `description`, markdown body cut at its
  `##` headings) into an ordinary skill file for review. It sets aside every other frontmatter key (`allowed-tools`, `domains`), because a
  skill grants nothing, and it never locks, enables or overwrites. `--reference` keeps the sections for `read_skill`; without it they become
  stage text and must fit a part (8,000 characters) or be chosen with `--section`.
- Limits, fixed in the code: a section 20,000 characters (the runner's result limit), 64 sections and 200,000 characters a skill, a skill file 256 KiB.
- The skill guidance template is version 2, because the frame gained the reference note.

## Amendments from M6.5: Claude Code plugin folder import (2026-11-22)

- **`ei plugins import FOLDER`** reads a plugin folder's `.claude-plugin/plugin.json`, `.mcp.json` and `skills/*/SKILL.md`, and writes
  an ordinary bundle for review. It opens only those files, follows no link, runs nothing, and never replaces a file. The bytes are
  parsed again before they are written.
- **Nothing widens.** Skills become reference skills enabled for no stage. A server is kept only when the tool lock's own rules accept
  it (an absolute, non-launcher command, or an https address with no secret in it); `${...}` placeholders are not expanded; environment
  values and headers are not copied, only environment *names* and a `Bearer ${NAME}` token as `bearer_env`. Commands, agents, hooks,
  output styles, monitors and `.lsp.json` are named and set aside, never read or run. Every skipped piece is printed with its reason.
- Decision 9 is unchanged: importing, like installing, starts nothing, contacts nothing, grants nothing and enables nothing.
- **`ei plugins search FILE.json`** lists a Claude Code `marketplace.json` (four fields read per plugin, all other keys ignored; sources
  classified as `path`, `github`, `url` or `other` and printed, never followed). It fetches, clones and installs nothing, because a
  marketplace names folders and repositories rather than hashable files; a `path` source in a local marketplace prints the
  `ei plugins import` command for it. The import is where the bundle is read and checked. Pinning a source by commit and hash-checking
  a fetched folder is not built.

## Amendments from M6.5: MCP resources (2026-11-23)

- **Resources are reached as two tools the client adds**, `list_resources` and `read_resource`, when a server declares the `resources`
  capability and has no tool of those names. Their descriptions and schemas are fixed in this project's code, not the server's.
  Because they are in the tool list they are pinned by the tools hash, granted to a stage only by name, offered to no stage by
  default, and returned as untrusted tool output. No new lock field, grant kind or code path in the runner.
- **A resource is read only on request**, by a stage the lock grants it, by the uri the model names: text only (a binary resource is noted
  as left out), a uri of one line and at most 2,000 characters, a listing of at most 200 entries. Nothing is subscribed to, and the client
  still announces no capabilities. A resource's content is not pinned, because it changes; the *ability* to read is pinned.
- **Consequence:** a server that declares resources and was locked earlier no longer matches its lock until it is locked again, which is the
  conservative result of a changed tool list.
- Not decided here: giving a run a resource as an *input* (a person's choice at the start of a run), and MCP prompts and OAuth.

