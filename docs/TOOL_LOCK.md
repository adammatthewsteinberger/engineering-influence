# The tool lock

Third-party tool servers (MCP servers) run only if a person has approved them, and only while they
are still what was approved. The approval is the **tool lock**, a TOML file you review like any other
commit. This is slice 4 of [ADR 0008](adr/0008-tools-for-the-model.md), built in parts.

**Status.** Built and tested: the lock's models and file format, a strict reader and writer, the MCP
client (over an abstract transport, tested with a fake), and the verifier. **Not built yet:** a real
transport that starts a server (4b), the `ei tools` commands (4b), offering a locked server's tools to
a stage and checking the lock at start (4c), and HTTP servers (4d). Nothing in a run reads a lock today,
so no third-party tool can be called.

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
protocol's published shape. It has been tested against a fake transport only: **not against a real
server**, which 4b adds.

- **It offers the server nothing.** It announces no capabilities. A request the server sends anyway is
  refused with `-32601`, except `ping`, so a server cannot ask this client to sample the model, read a
  root or prompt a person.
- **Everything a server sends is untrusted and bounded.** A malformed reply is an error. A tool list
  is cut off at 500 tools and 20 pages, and a server that sends more than 100 messages that are not the
  answer is cut off. A tool's answer is reduced to its text, and any other content is replaced by a
  note that it was left out.
- It speaks protocol versions `2025-06-18`, `2025-03-26` and `2024-11-05`.
