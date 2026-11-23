# Plugins

A **plugin** is one reviewed file that bundles [skills](SKILLS.md) and the definitions of tool servers
(MCP servers), so a person can look at everything in it at once, pin it by hash and install it. It is slice 6
of [ADR 0008](adr/0008-tools-for-the-model.md), built in two parts: **6a**, plugins installed from a file on
disk, and **6b**, marketplace indexes, which list plugin files and let a person download one.

**Installing a plugin starts nothing, contacts nothing, grants nothing and enables nothing.** That is the
whole design. A bundle is text from someone else, and the step that starts a tool server is `ei tools add`,
which a person runs on purpose. So `ei plugins add` does only two things with what it finds: it locks the
bundle's **skills** (each enabled for no stage) and it **prints** the `ei tools add` command for each server.

**Status.** Built and tested against fakes and real files: the bundle format, the plugin lock, `ei plugins`.
No plugin has been used in a run with a live model, and the downloader has only been run against a local test
server and a scripted address, never the real internet.

## A plugin file

One TOML file, named like the plugin:

```toml
# research_pack.toml
name = "research_pack"            # the same as the file name, without .toml
version = 1                       # a whole number from 1
description = "Sources and style for research."   # optional, one line, at most 300 characters

[[server]]                        # a remote server: an address, and the variable that holds its token
name = "docs"
url = "https://mcp.example.com/v1/mcp"
bearer_env = "DOCS_TOKEN"

[[server]]                        # a local server: an absolute command, and the variables it is given
name = "files"
command = ["/usr/local/bin/files-server", "/opt/files/server.js"]
env = ["FILES_ROOT"]

[[skill]]                         # a skill file's contents, as a table
name = "plain_style"
version = 2
description = "Short, plain sentences."

[skill.parts]
research = "Say where you read it."
outline = "Prefer short chapters."
```

- A **server** has a `name` (as in the tool lock) and **either** a `command` (with an optional `env` list) **or** a
  `url` (with an optional `bearer_env`). It is checked by the same rules the tool lock uses, so a plugin cannot
  describe a server the lock would refuse: the executable is an absolute path and not a launcher such as `npx`
  or `uvx`, the address is https with no user, query or fragment, and names are what the lock accepts. A
  command's parts must be printable text, at most 64 of them and 1,000 characters each.
- A **skill** is read by the same strict parser as a skill file, so everything in [SKILLS.md](SKILLS.md) applies:
  no invisible or control characters, parts capped at 8,000 characters, and no key but `name`, `version`,
  `description` and `parts`.
- **There is no key for a grant, for a stage to enable a skill for, or for anything else that would let a
  bundle decide what a model may do.** Any other key, anywhere, is refused and named.
- At most 16 servers and 16 skills, each named once, and at least one of either. A file is at most 512 KiB.

## Commands

```text
ei plugins import FOLDER [--name NAME] [--version N] [--out FILE]
ei plugins show FILE
ei plugins add [--lock PATH] [--skill-lock PATH] FILE
ei plugins list [--lock PATH]
ei plugins verify [--lock PATH] [--skill-lock PATH]
ei plugins remove [--lock PATH] [--skill-lock PATH] NAME
ei plugins search INDEX_OR_MARKETPLACE_JSON [TEXT]
ei plugins fetch INDEX NAME [--output DIR]
```

The plugin lock is `--lock`, else `EI_PLUGIN_LOCK`, else `ei-plugins.lock.toml`; the skill lock is
`--skill-lock`, else `EI_SKILL_LOCK`, else `ei-skills.lock.toml`.

- **`import`** reads a Claude Code plugin folder and writes a bundle to review (see below). It installs nothing.
- **`show`** reads a bundle and says what installing it would do, changing nothing. Read this first.
- **`add`** reads the file once, hashes those bytes and checks them strictly. Each skill goes into the skill lock
  through the same code `ei skills add` uses, enabled for no stage. A copy of the bundle is kept in `plugins/`
  beside the plugin lock, and the plugin lock records its SHA-256, the names of the servers it described and the
  hash each skill was locked under. It then prints each server as the command to run, for example
  `ei tools add --bearer-env DOCS_TOKEN --url https://mcp.example.com/v1/mcp docs`.
  It refuses a plugin that is already installed and skills that are already locked, **before writing anything**;
  to install a newer version, `remove` the old one first.
- **`list`** shows the installed plugins with their short hash, the skills installed and the servers described.
- **`verify`** re-hashes each kept bundle and checks that each skill it installed is still locked under the hash it
  was installed with. Exit `0` all match, `1` something does not, `2` setup trouble.
- **`remove`** deletes the bundle's copy and the skills it installed that are **still exactly what it installed**. A
  skill locked again with other text since belongs to the person now and is left, and named. A server it
  described stays in the tool lock if you locked it.

## Importing a Claude Code plugin

`ei plugins import FOLDER` turns a plugin folder written for Claude Code into the bundle format above, so it can be
read and then installed with `show` and `add`. It reads three things and lists the rest:

- `.claude-plugin/plugin.json` for the name and description (the folder's name if there is none);
- `.mcp.json` (or an `mcpServers` table inside `plugin.json`) for servers;
- `skills/*/SKILL.md`, each converted exactly as `ei skills import --reference` converts one: the sections become
  reference read through `read_skill`, and a skill is enabled for no stage.

Commands, agents, hooks, output styles, monitors and `.lsp.json` are **set aside and named**: a bundle grants
nothing and runs nothing, so none of them is read or executed. A server is carried over only if the tool lock would
accept it: a command with an absolute path that is not a launcher (`npx`, `uvx`, `docker` and the like are skipped,
because what they fetch cannot be hashed; install the server and write its real path), or a streamable-HTTP address
over https. A `${...}` placeholder in a command is never expanded, so that server is skipped. **Environment values
and headers are never copied**: only the *names* of environment variables are kept (you export them yourself), and
a header `Authorization: Bearer ${NAME}` becomes `bearer_env = "NAME"`; any other header skips the server. Every
skipped server or skill is printed with the reason, and an import that leaves nothing is refused.

The file is written new beside where you ran it (`NAME.toml`) and never replaces one; a bundle's name is its file's
name, so `--out` must end in `NAME.toml` (use `--name` to change the name). The bytes are parsed again before they
are written, so a file this command writes is a file `show` accepts. Read it: its text will be added to prompts
and its servers would be started, and it was written by whoever made the plugin.

## The plugin lock

`ei-plugins.lock.toml` records what was installed so it can be checked and undone:

```toml
version = 1

[[plugin]]
name = "research_pack"
version = 1
sha256 = "5d1c…"               # of the bundle's bytes
servers = ["docs", "files"]    # described, not installed

[plugin.skills]
plain_style = "9f2c…"          # the hash each skill was locked under
```

**A run never reads it.** What a run may do is in the tool lock and the skill lock, which a plugin only adds
skills to (enabled for no stage) or prints commands for. Nothing about a plugin changes a run until a person
runs `ei tools add` and `ei tools grant`, or `ei skills enable`, and reviews that change like any other commit.

## Marketplace indexes

A marketplace is **only an index**: a TOML file that lists plugin files, each with an address and the SHA-256
the file must have. It has no code, no skill text and no server definition, so reading one cannot lead to any of
them, and any key beyond these is refused:

```toml
version = 1

[[plugin]]
name = "research_pack"
version = 1
description = "Sources and style for research."
url = "https://plugins.example.com/v1/research_pack.toml"
sha256 = "5d1c…"                  # of the plugin file's bytes
```

`INDEX` is **a file on disk or an `https://` address**; any other kind of address is refused before anything is
contacted. An index lists at most 500 plugins and may be up to 512 KiB.

- **`search INDEX [TEXT]`** lists the plugins in an index, or those whose name or description contains the text,
  with each one's short hash and address. It installs nothing.
- **`fetch INDEX NAME [--output DIR]`** downloads one plugin file to `DIR` (default: here) as `NAME.toml`, and
  **installs nothing**. The bytes are hashed **before they are read as anything**, and a file whose SHA-256 is not
  the index's is discarded and never saved. Only then is it read as a plugin, which must be the plugin the index
  named at the version it named. It never overwrites an existing file. It ends by telling you to read the file
  with `ei plugins show` and install it with `ei plugins add`, which is the offline step described above.

What the download is held to: https only, to a public address (the URL policy `fetch_url` uses, asked each time,
so a name that resolves to this machine or its network is refused), sent to **the address that was checked** with
the name in TLS so the certificate is still verified, **no redirects, no cookies, no compression**, at most 512 KiB
and 30 seconds, and no credentials of any kind. An address in an index has no user, password, query string or
fragment, so nothing secret can be carried in one.

**A run never contacts a marketplace, and neither does `add`, `show`, `verify` or `remove`.** `search` and `fetch`
are the only commands that can use a network, only when a person runs them, and only with the `runtime` extra for
an `https://` address (a local index file needs nothing extra).

### Claude Code marketplaces (`marketplace.json`)

`ei plugins search FILE.json [TEXT]` (a path or an `https://` address ending in `.json`) reads a Claude Code
`marketplace.json` and **lists** what it names. It reads four things from each plugin (`name`, `description`,
`version`, `source`) and ignores every other key. A source is classified and printed, never followed:
`./folder` is a `path` inside the marketplace, `{"source": "github"}` a repository, `{"source": "url"}` or `git` an
address, anything else (or a `./` path that climbs out with `..`) `other`. For a marketplace on disk a `path`
source also prints the exact `ei plugins import FOLDER` command for the folder on this machine.

**Nothing is fetched, cloned or installed.** Unlike an index, a marketplace names folders and repositories, not one
file with a hash, so there is nothing here to verify a download against: you get a copy yourself, read it, and
`ei plugins import` it, which is where the bundle is checked. An entry that cannot be read is counted and left
out, not hidden; a duplicate name keeps the first. `plugins fetch` still works only with this project's TOML
indexes.

## What this does and does not give you

- **It gives you one thing to review and one hash to pin** for a set of skills and server definitions, and a
  way to undo the install. `show` lists every part of a bundle, including the text of every skill.
- **It does not vouch for anything.** A plugin's skills are trusted as installed once you enable them
  ([SKILLS.md](SKILLS.md#what-this-does-and-does-not-give-you)), and a server it describes is exactly as
  trustworthy as `ei tools add` makes it ([TOOL_LOCK.md](TOOL_LOCK.md)), which for a local server pins the
  files it runs and for a remote server pins only its address and what it advertises.
- **The hash proves you got the file the index described, not that anyone vetted it.** An index is only as
  trustworthy as whoever controls the host it came from, and so is every file it points to. What stands between
  you and a hostile plugin is that you read it (`ei plugins show` prints every skill's text and every server's
  command) before `add`, and that installing it enables nothing.
- The printed command is shell-quoted, so what you see is what would be typed. Read it before you run it:
  `ei tools add` **runs a local server once**, and a command a stranger wrote can do anything its user can.
- The kept copy is read through no link and refused if it is a link, a folder or too large, and the install
  writes it first and undoes everything if a later step fails. Nothing prevents a person with write access to
  the folder from changing a file; the hash is what turns that into a failure of `verify`.

## What is not built

Whatever a Claude Code plugin does beyond skills and MCP servers: its commands, agents, hooks and output styles are not
imported. Servers that need a launcher or a placeholder are not converted (they are named, so a person can install
them by hand). A `marketplace.json` is listed, not fetched: plugins named by a repository or an address are not downloaded, pinned
by commit or hash-checked. An index is still this project's own TOML.

Anything that vouches for a publisher: indexes and plugin files are not signed, so the hash is the only
integrity check. Nothing updates itself or checks an index for newer versions, a plugin cannot name another
plugin it depends on, and there is no registry service: an index is a file somebody publishes.
