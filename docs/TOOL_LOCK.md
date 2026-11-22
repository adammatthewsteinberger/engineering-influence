# The tool lock

Third-party tool servers (MCP servers) run only if a person has approved them, and only while they
are still what was approved. The approval is the **tool lock**, a TOML file you review like any other
commit. This is slice 4 of [ADR 0008](adr/0008-tools-for-the-model.md), built in parts.

**Status.** Built and tested: the lock's models and file format, a strict reader and writer, the MCP
client, the verifier, a **stdio transport that runs a server as a child process under limits**, and the
`ei tools add`, `list`, `verify`, `grant` and `revoke` commands, and (slice 4c) **the wiring into a run**:
a run that is given a lock starts and verifies each server, registers its tools, and offers a stage only
the tools the lock grants it. **Not built yet:** HTTP servers (4d). No third-party server has been run
by a live model, and none other than a small server written for the tests has been run at all.

## In a run

A model-backed run reads a lock only when **`EI_TOOL_LOCK`** names one. The file in the current directory
is not read, so a stray `ei-tools.lock.toml` starts nothing. At start, for each locked server in name order:

1. the locked **files** are compared, and a server whose files changed is **never started**;
2. the server is started with only the variables the lock names, and asked who it is and what it offers;
3. its **name, version and tools** are compared with the lock, and a **granted tool that cannot be offered**
   to a model (its schema is not an object) is refused;
4. each tool that can be offered is registered as `<server>__<tool>`.

Any difference stops the process at start with `TOOL_LOCK_MISMATCH` (naming the server and every problem),
and **stops every server already started**. A server that cannot be started or does not answer is
`TOOL_SERVER_UNAVAILABLE`. A run does not begin with a tool it was promised and cannot have.

**Registering a tool does not offer it.** A stage is offered its recipe's own tools plus the tools the lock
**grants that stage**, and the tool runner runs only what was offered, so a tool that exists but was not
granted is refused as "no tool named ..." even if the model asks for it. A stage the lock does not mention
gets none. Everything a locked tool returns goes through the same runner as the built-in tools: its
arguments are checked against the schema the server advertised, its answer (and the text of an error it
reports) is cut and wrapped as untrusted text, and it is journaled.

**The journal remembers which server answered.** A stored tool result is keyed by the tool, its arguments
and the tool's *revision*, which for a locked tool is the hash of the server's tools. A server that is updated
and locked again is asked again; a resumed run does not replay the old server's answers.

Servers stay running for the life of the process, one call at a time per server, and are stopped when the
runtime is closed. A server's session is limited to **four hours, 2 GiB of memory and 1 GiB of disk**
(fixed, not settings). A server that is stopped for passing a limit fails its later calls; it is not restarted.

## Grants

A grant says which stage may call which of a server's tools. It lives in the lock, so it is reviewed in the
same commit as the server it applies to:

```text
ei tools grant [--lock PATH] NAME STAGE TOOL [TOOL …]
ei tools revoke [--lock PATH] NAME STAGE [TOOL …]
```

- `grant` adds tools to a stage's list; it runs nothing. The tools must be ones the lock lists, and must be
  able to be offered under `<server>__<tool>`. There are **no wildcards**.
- `revoke` takes the named tools back, or all of the stage's if none are named. Revoking from a stage that
  has no grant is an error, so a misspelt stage is noticed.
- A stage name that no recipe uses is not an error here: the lock does not know the recipes, so the grant
  would simply never be used. `ei tools list` shows every stage's grants.

## The `ei tools` commands

```text
ei tools add [--lock PATH] [--env VAR …] [--replace] NAME -- COMMAND [ARG …]
ei tools list [--lock PATH]
ei tools verify [--lock PATH] [NAME …]
```

- **`add` runs the server.** Everything that can be refused is refused first: a bad name, a name already
  locked (unless `--replace`), a bad environment name, a command that does not exist, a launcher, an
  executable that cannot be read, and a script given by a relative path (give an absolute path, so the
  file locked is the file run). Then the server is started once, asked who it is and what it offers, and
  stopped, and the entry is written. It prints every tool and its description, cut and with control
  characters removed, because **the descriptions are written by the server: read them before you commit
  the lock.** Options go before `NAME`; an option after it gets a clear error.
- **`list`** shows what is locked and starts nothing.
- **`verify` runs each locked server**, but a server whose files changed is **never started**. It then
  compares the name, version and tools. A server that cannot be started or does not answer is a failed
  check, not a crash, so every server is reported. Exit `1` if any no longer matches, `2` for setup
  trouble or a name that is not locked.

## How a server is run

- A child process in its own session. Closing it kills the whole process group, then reaps the leader;
  the leader is never reaped earlier, so its id is still ours when the group is killed.
- **A bare environment:** `PATH`, `LANG`, `TZ`, `SYSTEMROOT` and `LC_*`, plus the variables the lock names
  (a name that is not set is an error). `HOME` and the temporary-directory variables point at the server's
  own throwaway directory (mode 0700), which is also its working directory and is removed when it stops.
  No API key or token reaches it unless the lock names it.
- **Limits, as for the build tools:** resident memory of the whole group, the size of that directory and the
  session's time are sampled every half second, and the server is stopped when it passes one. A limit is
  enforced to within what the server can use in one interval. Only the working directory counts for disk.
- **A line is bounded** (4 MiB) and a server that talks faster than it is read is slowed by a short queue.
  A line that is not a JSON object is refused. Its last 2,000 bytes of error output are quoted if it dies.
- **This is not a sandbox.** A server can still read any file the user can read, by absolute path, and use
  the network. Linux and macOS only (it needs process groups).

## The file

```toml
# Locked MCP tool servers. Written by `ei tools add`; review a change to this file like any commit.
# Nothing a run does changes it. A server whose files or advertised tools differ is not started.
version = 1

[[server]]
name = "files"
command = ["/usr/local/bin/node", "/opt/mcp/files/index.js"]
env = ["FILES_ROOT"]
server_name = "files-server"
server_version = "1.2.0"
tool_names = ["read_file", "write_file"]
tools_hash = "<SHA-256 of every tool the server advertised>"

[server.files]
"/opt/mcp/files/index.js" = "<SHA-256>"
"/usr/local/bin/node" = "<SHA-256>"

[server.grants]
research = ["read_file"]
```

- **`name`** is lowercase letters, digits and `-`, from a letter, up to 32 characters. A tool is offered
  to the model as `<name>__<tool>`, so `files__read_file`; the double underscore is why the server name
  has none. A tool whose name does not fit what the model providers accept (letters, digits, `-` and `_`,
  64 in all), or that does not take an object, is not offered.
- **`command`** starts with the absolute path of the executable. **`[server.files]`** holds the SHA-256 of
  that executable and of every file named in the arguments (the script it runs).
- **`env`** is the *names* of the variables the server is given, never their values. Values come from
  the environment when the server starts. Everything else is dropped by the allow-list environment.
- **`server_name`, `server_version`, `tools_hash`** are what the server reported when it was added.
  `tool_names` is the same list in words, so a refusal can say which tool was added or removed.
- **`[server.grants]`** is optional: for each stage, the tools it may call (sorted, each once, each one in
  `tool_names`). Without it no stage gets any of the server's tools. A lock written before grants existed
  is read as having none, and a lock with none is written without the table.

The file is read strictly: an unknown key, a missing one, a wrong or non-integer `version` or an entry
the model refuses is an error naming the entry, never something skipped. It is written whole to a
temporary name and renamed, with servers in name order, so two saves of one lock give the same bytes.

## What is checked

1. **The files, before anything is started.** Each locked file must exist and hash the same, and each
   file named in the command must be locked, so a script added to the arguments is noticed. Nothing
   is run to find this out.
2. **The server's report, after it starts.** Its name, its version and the hash of the tools it
   advertises must match. The hash covers every tool's name, description and schema, so a reworded
   description is a changed server. That matters because a description is where a hostile server
   hides instructions for the model.

## What a lock does not protect, and what is refused

- **Installed dependencies** (`node_modules`, `site-packages`) are not hashed, and neither is anything
  the server downloads or reads while it runs. A locked script is trusted code.
- **The check and the start are separate moments.** A file could change between them.
- **Launchers are refused**: `npx`, `pnpx`, `bunx`, `uvx`, `pipx`, `npm`, `pnpm`, `yarn`, `docker`,
  `podman` and `env` fetch or choose code that cannot be hashed here. Install the server, then lock the
  executable or script it really runs.
- A lock proves the server is the one that was approved. It does not make a server safe to approve.
  What a server's tools return is untrusted text like any other tool's, and the stage's tool allowlist
  still decides which tools a stage can call.

## The MCP client

`McpClient` speaks JSON-RPC 2.0 for `initialize`, `tools/list` and `tools/call`, written from the
protocol's published shape. It has been run against a small server written for the tests, over a real
process and pipes. **It has not been run against third-party MCP servers.**

- **It offers the server nothing.** It announces no capabilities. A request the server sends anyway is
  refused with `-32601`, except `ping`, so a server cannot ask this client to sample the model, read a
  root or prompt a person.
- **Everything a server sends is untrusted and bounded.** A malformed reply is an error. A tool list
  is cut off at 500 tools and 20 pages, and a server that sends more than 100 messages that are not the
  answer is cut off. A tool's answer is reduced to its text, and any other content is replaced by a
  note that it was left out.
- It speaks protocol versions `2025-06-18`, `2025-03-26` and `2024-11-05`.
