# Plugins

A **plugin** is one reviewed file that bundles [skills](SKILLS.md) and the definitions of tool servers
(MCP servers), so a person can look at everything in it at once, pin it by hash and install it. It is slice 6
of [ADR 0008](adr/0008-tools-for-the-model.md), built in two parts: this page is **6a, plugins installed
from a file on disk**. Marketplace indexes (6b) are not built.

**Installing a plugin starts nothing, contacts nothing, grants nothing and enables nothing.** That is the
whole design. A bundle is text from someone else, and the step that starts a tool server is `ei tools add`,
which a person runs on purpose. So `ei plugins add` does only two things with what it finds: it locks the
bundle's **skills** (each enabled for no stage) and it **prints** the `ei tools add` command for each server.

**Status.** Built and tested against fakes and real files: the bundle format, the plugin lock, `ei plugins`.
No plugin has been used in a run with a live model, and no bundle has come from anywhere but a local file.

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
ei plugins show FILE
ei plugins add [--lock PATH] [--skill-lock PATH] FILE
ei plugins list [--lock PATH]
ei plugins verify [--lock PATH] [--skill-lock PATH]
ei plugins remove [--lock PATH] [--skill-lock PATH] NAME
```

The plugin lock is `--lock`, else `EI_PLUGIN_LOCK`, else `ei-plugins.lock.toml`; the skill lock is
`--skill-lock`, else `EI_SKILL_LOCK`, else `ei-skills.lock.toml`.

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

## What this does and does not give you

- **It gives you one thing to review and one hash to pin** for a set of skills and server definitions, and a
  way to undo the install. `show` lists every part of a bundle, including the text of every skill.
- **It does not vouch for anything.** A plugin's skills are trusted as installed once you enable them
  ([SKILLS.md](SKILLS.md#what-this-does-and-does-not-give-you)), and a server it describes is exactly as
  trustworthy as `ei tools add` makes it ([TOOL_LOCK.md](TOOL_LOCK.md)), which for a local server pins the
  files it runs and for a remote server pins only its address and what it advertises.
- The printed command is shell-quoted, so what you see is what would be typed. Read it before you run it:
  `ei tools add` **runs a local server once**, and a command a stranger wrote can do anything its user can.
- The kept copy is read through no link and refused if it is a link, a folder or too large, and the install
  writes it first and undoes everything if a later step fails. Nothing prevents a person with write access to
  the folder from changing a file; the hash is what turns that into a failure of `verify`.

## What is not built

**Marketplace indexes (6b).** A marketplace will be only an index of plugin files, each with an address and a
hash, and a person will fetch one with a command, never a run: `ei plugins add` will check the downloaded
bytes against the index's hash before reading them. Until then a plugin is a file you already have.
