# Skills

**BLUF:** A skill is a piece of text a person chose to add to one stage's prompt: a house style, a checklist, a
way of reading sources. It is data, with no command, tool or address, so installing one cannot run anything or
give a stage a tool. A hash pins its exact text, the lock says which stages may see it, and a run reads the lock
only when `EI_SKILL_LOCK` names one.

A **skill** is text a person chose to add to a stage's prompt: a house style, a checklist, a way of
reading sources. It is slice 5 of [ADR 0008](adr/0008-tools-for-the-model.md). A skill is **data**. It has no
command, no tool, no address and no blanks to fill, so installing one cannot run anything, reach
anything or give a stage a tool it did not have. It can only change what the model is asked.

**Status.** Built and tested against fakes and a scripted local model server: the skill file format, the
lock, `ei skills`, and the wiring into a model-backed run. No skill has been run by a live model.

## A note clipped to the order

> **Daniel:** I have a house style. Can I not just put it in the prompt?
>
> **Professor Feynman:** You can. What happens when someone edits the style a month later and does not tell you?
>
> **Daniel:** My books change and I do not know why.
>
> **Professor Feynman:** That is what the lock prevents. A skill is a small file whose bytes are hashed and
> written in a lock you review. Change one character and the run refuses to start until a person locks it again.
> The text is also clipped to the end of the stage's request, like a note on a kitchen order, never into the fixed
> system part.
>
> **Daniel:** And only the stages I name see it?
>
> **Professor Feynman:** Only those, at most four skills each, no wildcards. A skill enabled for no stage is never
> shown to a model. Notice what a skill cannot do: it cannot add a tool, change an output limit or touch the
> system prompt. Where the picture breaks: a note on an order can still say something foolish, and the cook will
> follow it. A skill is trusted text, because it is meant to instruct.
>
> **Daniel:** So the lock protects me from silent changes, not from my own bad advice. I will keep each skill
> short and read it before I enable it.

## Skills at a glance

| Question | Answer |
|---|---|
| What is it? | One TOML file of text, one part per stage it speaks to |
| What pins it? | The hash of its bytes in `ei-skills.lock.toml` |
| Who sees it? | Only the stages the lock enables it for, at most four skills per stage |
| Where does it go in the prompt? | The end of the user part, never the system part |
| Can it give a stage a tool? | No. A skill with reference sections adds only the read-only `read_skill` tool |
| Is it proven against a live model? | No |


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

Each part is named for **the stage it speaks to** (`brief`, `positioning`, `research`, `outline`, `metadata`, `draft`, `revise_structure`, `revise_lines`, `copy_edit`; `assemble` and `audit` make no model call, so a skill for either does nothing) and
holds the text for that stage. A skill with no text for a stage never reaches it.

### Reference sections: read on request

A long reference does not belong in every prompt. A skill may instead (or also) have a `[reference]` table of
`"Section title" = "text"`:

```toml
name = "research_methodology"
version = 1

[reference]
"Source Evaluation" = "Judge a source with SIFT: stop, investigate the source, find better coverage, trace the claim."
"Database Searching" = "Use Boolean operators and note the date of every search."
```

A stage the skill is enabled for gets an **index** at the end of its prompt (one line for each section, with its length) and
the read-only **`read_skill`** tool. The model asks for a section by naming the skill and the title, and gets that
section's text back, as a tool result, which is wrapped as untrusted like any other. The sections themselves are never added to the prompt, so a
skill costs a prompt a line for each section until the model reads one.

- **A stage reaches only what its own prompt lists.** `read_skill` is shared by every stage that has a reference skill, so it
  refuses a call for a skill or section the calling stage's prompt does not list (the same check `fetch_url` uses on addresses). A
  skill enabled for `outline` cannot be read from `research`.
- A reference skill can be enabled for **any** stage, because it has no per-stage text. Limits: a section is at most 20,000
  characters (so it is never cut), a skill has at most 64 sections and 200,000 characters of them, and a title is one line of at most
  100 characters with no angle brackets.
- `read_skill` is offered in drafting and the editing passes as well as the earlier stages, and only when the skill is enabled for that stage.

Reading is strict. Any other key (a misspelt one, `command`, `tools`, `url`, `untrusted`) is refused and
named. The file must name itself the same as its file name. A file is at most 64 KiB, a skill at most 32
parts, and a part at most 8,000 characters.

**Text a reviewer cannot see is refused.** The text a person approved is exactly the text a model sees, so
it is held to what a person can read: control characters, zero-width and bidirectional marks
(U+200B, U+202E and the like), line and paragraph separators, private-use and unassigned code points are
all errors, and the error names the character. Newline and tab are the only controls allowed. These are
the usual way to hide an instruction in text that looks harmless in review.

## Importing a `SKILL.md`

Most skills in the wild (the Vibey and Claude ones among them) are a `SKILL.md`: a `---` block of `key: value` lines,
then markdown. `ei skills import` turns one into the skill file above, so it can be reviewed and locked like any other.

```text
ei skills import SOURCE (--stage STAGE [--stage STAGE ...] | --reference) [--section TITLE ...] [--name NAME] [--version N] [--out FILE]
```

`SOURCE` is the `SKILL.md` or the folder that holds it. Nothing else in the folder is read. It writes
`NAME.toml` here (or `--out`), **never replaces a file**, and **locks and enables nothing**. It prints the file's
path and what it kept, and tells you to read the file before you lock it with `ei skills add`.

- **You choose which sections go to which stages.** The body is cut at its `##` headings (a `##` line inside a
  code fence is not a heading), and text before the first one is the section `Overview`. `--section "Source
  Evaluation"` (repeat it) keeps only those, by title, ignoring case; with none, every section is kept. Each
  stage you name gets the same text, with the headings kept.
- **Nothing is cut to fit.** A part holds 8,000 characters and a `SKILL.md` is usually longer (the median Vibey skill is
  12 KB, the largest 58 KB). When the chosen text is too long, the error lists every section with its length so you can
  pick, for example, just `Source Evaluation` and `Database Searching` out of a 26 KB methodology reference. A skill
  file larger than the lock reads (64 KiB) is refused here, with the reason, rather than after you have committed to it.
- **`--reference` keeps the sections for on-demand reading** instead of as stage text (see "Reference sections" above): each chosen
  section stays separate, without its heading, and `--stage` is not allowed with it. A reference section may be up to 20,000
  characters, far past a part's 8,000, so a methodology reference usually imports whole. The skill is then enabled with
  `ei skills enable NAME STAGE` for each stage that should be able to read it.
- **The frontmatter must have a one-line `name` and `description`** (quoted or plain); a block scalar is refused rather than
  guessed at. **Every other key is read and set aside**, never used, and named in the output: `allowed-tools`, `domains`,
  a list under a key. A skill here is text and grants nothing, so a `SKILL.md` that asks for a tool gets no tool.
- **The name** is the file's, lower-cased with hyphens and spaces made underscores (`research-methodology` becomes
  `research_methodology`), unless you give `--name`. A name that cannot be made safe says so.
- **The description** is cut at a word to 300 characters with `...` when it is longer (real ones run past 1,000), and the
  output says it was. It is shown in lists and is never part of a prompt.
- Text a reviewer could not see is refused with the character named, exactly as for any skill.

Two ways to use a methodology reference. As **reference** (the model reads what it needs):

```bash
ei skills import ~/refs/research-methodology --reference
ei skills add research_methodology.toml
ei skills enable research_methodology research
```

Or as **stage text** (always in the prompt), giving the research stage two sections:

```bash
ei skills import ~/refs/research-methodology --stage research \
  --section "Source Evaluation" --section "Database Searching"
ei skills add research_methodology.toml
ei skills enable research_methodology research
```

The skills themselves are not part of this repository; you install them from your own copy.

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
ei skills import SOURCE --stage STAGE [--section TITLE] [--name NAME] [--version N] [--out FILE]
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
- **The prompt version records it.** A stage with skills sends `stage_outline@1+skill_guidance@2:<digest>`,
  where the digest covers each skill's name, version and hash. A resumed run replays an answer only for the
  same text, and a stage with no skill enabled sends exactly the prompt and version it always did.
- **Nothing else changes, with one exception.** A skill does not add a tool of its own, change the output cap or touch
  the system prompt. Tool grants stay in the tool lock and the recipe. The exception is a skill with reference sections:
  a stage it is enabled for is also offered the built-in, read-only `read_skill` tool, which can return only the sections that stage's
  prompt lists. It cannot read a file, reach an address or run anything.

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

A plugin ([PLUGINS.md](PLUGINS.md)) is a bundle of skills and tool server definitions that a person installs from a
file; its skills become ordinary skills here, enabled for no stage. Nothing fetches a skill from a network during a
run, and a run never contacts a marketplace. A Claude Code plugin folder is read by `ei plugins import`, and a marketplace index by `ei plugins search` and `fetch` ([PLUGINS.md](PLUGINS.md)).
