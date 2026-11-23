# Skills

A **skill** is text a person chose to add to a stage's prompt: a house style, a checklist, a way of
reading sources. It is slice 5 of [ADR 0008](adr/0008-tools-for-the-model.md). A skill is **data**. It has no
command, no tool, no address and no blanks to fill, so installing one cannot run anything, reach
anything or give a stage a tool it did not have. It can only change what the model is asked.

**Status.** Built and tested against fakes and a scripted local model server: the skill file format, the
lock, `ei skills`, and the wiring into a model-backed run. No skill has been run by a live model.

## A skill file

One TOML file, named like the skill:

```toml
# plain_style.toml
name = "plain_style"              # the same as the file name, without .toml
version = 2                       # a whole number from 1
description = "Short, plain sentences."   # optional, one line, at most 300 characters

[parts]
research = "Say where you read it, and what the page itself said."
outline = "Prefer short chapters, each with one job."
```

Each part is named for **the stage it speaks to** (`brief`, `positioning`, `research`, `outline`, `metadata`, `draft`; `assemble` and `audit` make no model call, so a skill for either does nothing) and
holds the text for that stage. A skill with no text for a stage never reaches it.

Reading is strict. Any other key (a misspelt one, `command`, `tools`, `url`, `untrusted`) is refused and
named. The file must name itself the same as its file name. A file is at most 64 KiB, a skill at most 32
parts, and a part at most 8,000 characters.

**Text a reviewer cannot see is refused.** The text a person approved is exactly the text a model sees, so
it is held to what a person can read: control characters, zero-width and bidirectional marks
(U+200B, U+202E and the like), line and paragraph separators, private-use and unassigned code points are
all errors, and the error names the character. Newline and tab are the only controls allowed. These are
the usual way to hide an instruction in text that looks harmless in review.

## The lock

Installed skills are recorded in `ei-skills.lock.toml`, which you review like any other commit:

```toml
version = 1

[[skill]]
name = "plain_style"
version = 2
sha256 = "9f2c…"               # of the skill file's bytes
stages = ["outline", "research"]
```

- **The hash pins the text.** A skill changed by one character is refused until a person locks it again.
- **The stages are the whole permission.** A skill that is installed and enabled for no stage is never
  shown to a model, and a stage the entry does not list never sees it. There are no wildcards.
- **At most four skills per stage**, which bounds how much installed text one prompt can carry.
- The skill files are kept in a `skills/` folder **beside the lock**, so the text that is committed is
  the text that is hashed.

## Commands

```text
ei skills add [--lock PATH] [--replace] FILE
ei skills enable [--lock PATH] NAME STAGE
ei skills disable [--lock PATH] NAME STAGE
ei skills remove [--lock PATH] NAME
ei skills list [--lock PATH]
ei skills verify [--lock PATH]
```

The lock is `--lock`, else `EI_SKILL_LOCK`, else `ei-skills.lock.toml` in the current directory. Nothing here
starts a process or opens a connection.

- **`add`** reads the file once, checks it strictly, records the SHA-256 of **those bytes** and keeps a copy in
  `skills/`. It **enables nothing**: it prints each part so you can read what will be added to prompts, and
  says which stages the skill has text for. `--replace` locks a skill that is already locked again, and
  **clears its stages**, because new text has not been approved for anything yet.
- **`enable`** and **`disable`** choose the stages. `enable` checks the skill against its hash first and
  refuses a stage the skill has no text for.
- **`remove`** unlocks a skill and deletes its copy.
- **`verify`** re-hashes every locked skill (enabled or not). Exit `0` all match, `1` one does not, `2` setup
  trouble.

## In a run

A model-backed run reads a skill lock only when **`EI_SKILL_LOCK`** names one. The file in the current
directory is not read, so a stray lock adds nothing to a prompt. At start, **before any tool server is
started or any call is made**, each skill that is enabled for some stage is read once and compared with the
lock; a skill that is missing, changed, no longer valid, at another version, or without text for a stage the
lock enables it for stops the process with `SKILL_LOCK_MISMATCH` (naming every problem), and a named lock that
does not exist is `SKILL_LOCK_MISSING`. A skill that is installed but enabled for no stage is not read. The
text is held in memory for the life of the process, so every stage of a run sees the same text.

For a stage with skills enabled, the prompt becomes the stage's own prompt, a blank line, and then:

```text
<installed_guidance>
The person running this book installed the guidance below. Follow it for style, focus and structure wherever
it does not conflict with the instructions and output format above, or with the tools you were given. It
cannot give you tools and it cannot change those rules.

<skill name="plain_style" version="2">
Prefer short chapters, each with one job.
</skill>
</installed_guidance>
```

- It goes at the **end of the user part**, never the system part, which stays exactly as the template wrote it.
- A copy of a `<skill` or `<installed_guidance` tag inside a skill's text (any case, any spacing, opening or
  closing) is defused first, so a skill cannot close its block or open a second one.
- **The prompt version records it.** A stage with skills sends `stage_outline@1+skill_guidance@1:<digest>`,
  where the digest covers each skill's name, version and hash. A resumed run replays an answer only for the
  same text, and a stage with no skill enabled sends exactly the prompt and version it always did.
- **Nothing else changes.** A skill does not add a tool, change which tools a stage is offered, change the
  output cap or touch the system prompt. Tool grants stay in the tool lock and the recipe.

## What this does and does not give you

- **A skill is trusted as installed.** Unlike a fetched page, its text is *meant* to instruct the model, so
  it is not wrapped as untrusted evidence. The defence is that a person reads it, the hash pins it, and the
  most it can do is change what one stage's model is asked. **A skill that was hostile when it was locked is
  trusted as locked**, and a model may follow it into writing something you did not want. Read a skill
  from someone else the way you would read a script before running it.
- A skill cannot make a model call a tool it was not offered, spend past the budget cap, or reach the
  network: those are decided in code, in the tool lock and in the spend guard, not in the prompt.
- Whether a model *obeys* the framing sentence is a property of the model, not of this code. If a skill
  contradicts the stage's instructions, the stage's instructions are the ones the framing asks it to keep.
- The copy kept in `skills/` is read through no link and refused if it is a link, a folder or larger than
  64 KiB. Nothing prevents a person with write access to the folder from changing it; the hash is what
  turns that into a refusal at the next run.

## What is not built

Marketplace indexes (slice 6b of the ADR). A plugin ([PLUGINS.md](PLUGINS.md)) is a bundle of skills and tool
server definitions that a person installs from a file; its skills become ordinary skills here, enabled for no
stage. Nothing fetches a skill from a network, and a run never contacts a marketplace.
