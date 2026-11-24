# The tool lock

**BLUF:** A tool server (an MCP server) runs in a book run only if a person approved it, and only while it is
still what was approved. The approval is the tool lock, a TOML file you review like any other commit. It pins the
server's files, its name and version, and a hash of every tool it advertises, and it says which stage may call
which tool. A run reads a lock only when `EI_TOOL_LOCK` names one.

Third-party tool servers (MCP servers) run only if a person has approved them, and only while they
are still what was approved. The approval is the **tool lock**, a TOML file you review like any other
commit. This is slice 4 of [ADR 0008](adr/0008-tools-for-the-model.md), built in parts.

**Status.** Built and tested: the lock's models and file format, a strict reader and writer, the MCP
client, the verifier, a **stdio transport that runs a server as a child process under limits**, and the
`ei tools add`, `list`, `verify`, `grant` and `revoke` commands, and (slice 4c) **the wiring into a run**:
a run that is given a lock starts and verifies each server, registers its tools, and offers a stage only
the tools the lock grants it, and (slice 4d) **remote servers over HTTP**. No third-party server has been
run by a live model, and no server other than small ones written for the tests has been run at all; the
HTTP transport has only been run against a scripted server, never over a real network.

## A guest list with a photograph

> **Daniel:** I want the research stage to use a tool server I found. Why can I not just point it at the server
> and let it go?
>
> **Professor Feynman:** You are the caretaker of a building. A visitor says he is from the gas company. What do
> you check?
>
> **Daniel:** His name on the list. And his badge.
>
> **Professor Feynman:** Two checks, then. The lock is both. First, the list: which server, and which of its tools
> a stage may call, written down in a file you reviewed. Second, the badge: a hash of the server's files and of
> everything it says about itself, checked every time it starts. If either changed, it does not come in.
>
> **Daniel:** A hash of what it says about itself? Why would that matter?
>
> **Professor Feynman:** Because a tool's description is where a hostile server hides instructions for the model.
> Reword one word and the hash changes, and the run stops at start with `TOOL_LOCK_MISMATCH` naming the server.
>
> **Daniel:** So a lock means the server is safe.
>
> **Professor Feynman:** No, and this is where the picture breaks. A badge proves it is the person you approved.
> It does not prove that person is honest. Dependencies are not hashed, a remote server is pinned only by its
> address, and what a server returns is still untrusted text. You decide whether to approve; the lock makes sure
> it stays what you approved.
>
> **Daniel:** The lock keeps it the same as what I approved, and the approving is still my job. I will read the
> server before I add it.

## The lock at a glance

| Question | Answer |
|---|---|
| Where is it read from? | Only the file `EI_TOOL_LOCK` names. A file in the current directory is ignored |
| What is pinned for a local server? | Its files by hash, its name, its version and a hash of its tools |
| What is pinned for a remote server? | Its address and what it advertises, and nothing else |
| Who may call a tool? | Only a stage the lock grants it to, with no wildcards |
| What if anything differs? | The process stops at start: `TOOL_LOCK_MISMATCH`, or `TOOL_SERVER_UNAVAILABLE` |
| Is it proven against a live model? | No. Only small servers written for the tests have been run |


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
A remote server has the four hours and the 30-second request limit; memory and disk are the other
machine's, not ours. For a remote server step 1 has nothing to compare, and step 2 is a connection to its
address instead of a process.

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
ei tools add [--lock PATH] [--bearer-env VAR] [--replace] --url URL NAME
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
- **`add --url`** contacts a remote server once instead of running a command. The address, the name and the
  variable's name are checked first, then the server is asked who it is and what it offers and the entry is
  written. It takes no command and no `--env`, and `--bearer-env` goes only with `--url`. The output says
  plainly that **only the address and what the server advertises are locked, not its code**.
- **`list`** shows what is locked and starts nothing. A remote server shows its `url:` and, if it has one,
  its `bearer:` variable.
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

## Remote servers (HTTP)

A server can also be reached at an address, over the *Streamable HTTP* transport of MCP: one POST per
message, the answer coming back as JSON or as server-sent events. A remote entry has a `url` and no command,
files or `env`; it may name one variable, `bearer_env`, whose value is sent as `Authorization: Bearer …`.

**What is pinned is weaker than for a local server, and this is stated rather than hidden.** A local
server's files are hashed, so changed code is not started. A remote server's code is somebody else's and can
change on any day, so what the lock pins is the **address** and what the server **advertises** (its name,
version and a hash of its tools). The start-up check is the only check there is. A server that behaved when it
was locked and changes later is caught only if it changes what it advertises, and one that was hostile when it
was locked is trusted as locked. Prefer a local server whenever there is one.

The rules a remote server is held to:

- **https only, and only to a public address.** The address is checked by the same URL policy as `fetch_url`
  (`PublicHttpsUrlPolicy`), **before every request**, so a name that has come to resolve to the machine's own
  network, a private range or a cloud metadata address is refused. **A server on this machine or this network
  cannot be reached this way**; run it over stdio instead.
- **No redirects, ever.** A 3xx is an error. A server cannot send the client, or its token, anywhere else.
- **Nothing that could hold a secret is in the address.** The lock refuses a user and password, a query string
  and a fragment, because the lock is committed. The credential is a named environment variable, read when the
  connection is made; a variable that is unset, or whose value is not a printable token with no spaces, refuses
  the server rather than sending a blank or broken header. It is never written into an error message, which
  names the host alone.
- **No cookies**, no compression, a generic user agent.
- **Every reply is bounded:** at most 4 MiB, at most 128 messages per request, and 30 seconds from the first
  byte sent; a stream is read until the answer to the request has come, and the rest is not read.
- **The session** is the server's `Mcp-Session-Id`, kept from the first reply, and the protocol version it
  agreed, sent on later requests. Closing the session sends a DELETE whose failure is ignored.
- **The client opens no stream of its own**, so messages a server starts (sampling, roots, notifications) have
  nowhere to arrive; as for a local server, the client offers nothing, and a request that comes inside a reply
  is refused (or answered, for `ping`).

Failures keep a stable code: `MCP_URL_REFUSED` (the policy), `MCP_REDIRECT_REFUSED`, `MCP_AUTH_REFUSED` (401 or
403), `MCP_SESSION_ENDED` (the server forgot the session), `MCP_SESSION_EXPIRED` (our four hours),
`MCP_REPLY_INVALID` (too long, not JSON, compressed, the wrong type), `MCP_HTTP_ERROR` (any other status).
A timeout, a dropped connection, 408, 425, 429 and 5xx are transient. At run start they all arrive as
`TOOL_SERVER_UNAVAILABLE`, or keep their own code where the failure has one.

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

A remote server's entry has an address in place of the command and no files table:

```toml
[[server]]
name = "docs"
url = "https://mcp.example.com/v1/mcp"
bearer_env = "DOCS_TOKEN"
server_name = "docs-server"
server_version = "2.0.0"
tool_names = ["search"]
tools_hash = "<SHA-256 of every tool the server advertised>"

[server.grants]
research = ["search"]
```

- **`name`** is lowercase letters, digits and `-`, from a letter, up to 32 characters. A tool is offered
  to the model as `<name>__<tool>`, so `files__read_file`; the double underscore is why the server name
  has none. A tool whose name does not fit what the model providers accept (letters, digits, `-` and `_`,
  64 in all), or that does not take an object, is not offered.
- **`command`** starts with the absolute path of the executable. **`[server.files]`** holds the SHA-256 of
  that executable and of every file named in the arguments (the script it runs).
- **`url`** (instead of `command`, `env` and `[server.files]`) is an `https` address with a host and a path,
  at most 2048 printable characters, **no user, password, query or fragment**. **`bearer_env`** is the name of
  the variable that holds its token, optional, and only with `url`. Exactly one of `command` and `url`.
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
- **A remote server is pinned by its address and what it advertises, and nothing else.** See above.
- **The connection is pinned to the address that was checked.** The name is resolved once, every address is
  judged by the URL policy, and the request goes to the first one with the name in the `Host` header and in
  TLS, so the certificate is still checked against the name. A name that resolves differently a moment later
  cannot send a request inward (DNS rebinding). Only one address is tried: if it is down the request fails
  and is transient, rather than falling back to another. A proxy named in the environment receives the
  address, not the name.
- **Launchers are refused**: `npx`, `pnpx`, `bunx`, `uvx`, `pipx`, `npm`, `pnpm`, `yarn`, `docker`,
  `podman` and `env` fetch or choose code that cannot be hashed here. Install the server, then lock the
  executable or script it really runs.
- A lock proves the server is the one that was approved. It does not make a server safe to approve.
  What a server's tools return is untrusted text like any other tool's, and the stage's tool allowlist
  still decides which tools a stage can call.

## Resources

A server that declares the MCP `resources` capability gets **two tools added by this client**, `list_resources` and
`read_resource`. Their descriptions and schemas are fixed in this project's code and are not the server's, so a server
cannot put instructions in them. They are in the tool list, which means everything above applies to them unchanged:
they are pinned by the lock's tools hash, appear in `ei tools list` and `verify`, are offered to **no stage unless
granted by name** (`ei tools grant files research list_resources read_resource`), and their results are wrapped as
untrusted tool output like any other.

- `list_resources` sends `resources/list` and returns one line per resource (uri, then name and type), at most 200, with the
  rest counted. `read_resource` takes a `uri` of one line and at most 2,000 characters and sends `resources/read`, and
  returns the **text** of what comes back; a binary resource is noted as left out and its bytes are never passed on.
- A server that already has a tool named `list_resources` or `read_resource` gets neither of ours, and its own tool is
  called as any tool.
- **Nothing is subscribed to**, and no resource is read unless a granted stage's model asks for it by uri. A resource's
  content can change between reads, so unlike the tool list it is not pinned.
- **A server that declares resources and was locked before this change no longer matches its lock**, because its tool
  list now has two more tools: `ei tools verify` names them, and `ei tools add --replace` locks it again.
- This is the way a model reads a server's resources; it is not yet a way to give a run a resource as an input.

## The MCP client

`McpClient` speaks JSON-RPC 2.0 for `initialize`, `tools/list`, `tools/call` and, for the two resource tools above,
`resources/list` and `resources/read`, written from the
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
