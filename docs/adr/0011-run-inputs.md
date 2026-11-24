# ADR 0011: Run inputs are untrusted text carried inside the brief

Status: proposed

## Context

A run's only input is the brief's one `idea`. A person who has notes, an excerpt, a draft or reference text has no way to
give it to the run, and the plan (M6.5) asks for pasted text and files. Nothing started a run when this was written (`ei book create` was M8; it now exists), so
whatever is decided here has to hold for every surface that will: the CLI, the API, MCP and the SDK.

Anything a person hands over may have been written by someone else (a page they copied, a file they were sent). It has to
reach a model as **evidence, never as instructions**, and it must not be able to widen what a stage may call.

## Decision

1. **An input is a `RunInput`**: a name (lowercase letters, digits, dots, hyphens, underscores; at most 60), plain text, and an
   origin (`pasted` or `file`). A line break and a tab are allowed; every other control, format, private-use or invisible
   character is **refused**, never cleaned, by the rule a skill's text is held to. The text is at most 50,000 characters and is never cut.
2. **Inputs live in the brief** (`BookBrief.inputs`): at most 8, each name once, 200,000 characters in all. They are stored with the
   run (the run's JSON gains `brief.inputs`), so a run carries what it was given, a resumed run sees the same text, and a
   run stored before this existed loads with none. Brief v1 gains an optional `inputs` list: an additive change that
   leaves every existing brief reading the same, as the contract promised for later compatible versions.
3. **Files are read here only as plain text** (`.txt`, `.md`, `.markdown`, UTF-8, at most 256 KiB, no link followed). A
   leading byte-order mark is dropped and line endings are made `\n`; a file with a hidden character is refused. PDF and HTML
   files need an extractor and are not read yet.
4. **Every input is untrusted.** It will reach a prompt only inside an `<untrusted>` block, like the brief and the research. It
   grants nothing: no input can name a tool, enable a skill or change a budget, and the stages' tool grants are unchanged.
5. **The digest of each input is its SHA-256**, so a person (and later the journal) can tell which text a run used.

## Consequences

- The surfaces that start a run (M8) pass inputs through the brief and need no new storage.
- A large reference is limited to 50,000 characters an input. A longer text is a reference skill (`read_skill`), which is read on
  request, not carried in every prompt.

## Amendment: inputs in the prompts

- **Three stages carry the inputs**: `brief`, `research` and `outline`, through an `inputs` blank that is listed as untrusted, so it is
  wrapped in `<untrusted name="inputs">` and any copy of that tag inside it is defused. Each input is shown under a heading made only
  of its validated name, its origin and the first 12 digits of its SHA-256, then its text. With none, the block says `not given`.
  The templates are now `stage_brief@2`, `stage_research@2` and `stage_outline@4`, so the journal never replays an answer written
  for the old prompt.
- **`positioning`, `metadata` and the editing stages do not carry them.** They read the brief and the outline, which were written from
  the inputs. **Drafting does not either**: its grounding is the outline and the research, and the inputs would repeat in every chapter's
  call. Drafting from a passage the author supplied is a separate decision.
- **The research prompt says the material is not a source**: a fact still needs a page the model read, so an input can point the research
  at something but cannot stand in for a citation.
- **Inputs grant nothing.** The system part, the tools offered and the stage's grants are identical with and without inputs (tested).
- **Known gap:** the model's context window is checked before drafting and editing, not before these three stages. Inputs of up to
  200,000 characters (about 50,000 tokens) can overrun a small model, and the provider's error is what the run would show.

