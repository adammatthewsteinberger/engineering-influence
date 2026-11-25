# ADR 0010: Chapters are drafted in order, inside one stage

Status: proposed

## Context

The plan for the non-fiction stages (M6) asks for per-chapter drafting as a **fan-out with an atomic join
counter and a concurrency cap**, and also for **a rolling summary and a fact tracker carried across
chapters**. Those two do not fit together: a summary of the chapters before this one needs those chapters to
exist, so chapters drafted at the same time cannot be given each other's summaries.

The machinery that exists points the same way:

- A `StagePlan` is a fixed, ordered tuple of distinct stage names, stored with the run when it starts, before the
  outline exists and so before the number of chapters is known. `AdvanceRun` walks it one stage at a time and makes
  duplicate deliveries safe with compare-and-swap.
- The M5 `ContextAssembler` was built for drafting in order: it fits the style, the grounding, the beats, as many of
  the newest prior-chapter summaries as will fit, and the tail of the previous chapter into a token budget.
- Every model call is journaled by a key made from the request, so a call that is repeated with the same
  request is replayed for nothing.

On 2026-11-22 the maintainer chose to draft the chapters **in order, in one stage**, and to leave parallel
fan-out for after 1.0.

## Decision

1. **A non-fiction plan gets one `draft` stage after `outline`.** It does not change how runs work: no sub-stages,
   no plan that grows, no new queue message and no join table. The stage takes the outline's chapters in order, in a
   single execution.

2. **The outline is a contract.** The `stage_outline` template tells the model to write each chapter as
   `## Chapter N: Title`, then `Purpose:`, `Beats:` and `Claims to source:` (bullets) and `Leads to:`. An
   `OutlineParser` reads that strictly into an `Outline` of `ChapterOutline`s (at most 50 chapters, numbered 1, 2, 3
   with no gaps, one-line bounded texts), and a **check run when the outline stage finishes** refuses an answer it
   cannot read, before it is stored. A malformed outline therefore stops the run at the outline, not one stage later
   after drafting has been paid for. A model's preamble before the first heading and a closing paragraph after a blank
   line are ignored; hidden and control characters are removed.

3. **Each chapter is drafted from what came before it.** For chapter *n* the
   context assembler is given the book's style (from the positioning), the grounding (the outline and the research
   notes), the chapter's beats, the summaries of chapters 1 to *n*−1 and the tail of chapter *n*−1. One model call,
   with no tools, drafts the chapter; a second summarizes it. They are stored as `chapter_NN.md` and `summary_NN.md`
   (two digits). Everything that came out of a model or off the web goes into a later prompt inside an `<untrusted>`
   block, as every other stage does.

4. **A chapter is done when both of its files exist, and a repeated execution skips done chapters.** A stage that
   fails or is redelivered part-way through starts over at the first chapter that is not done. Because a repeated model
   call is replayed from the journal for nothing, even a chapter that is redrafted costs nothing if its request is
   unchanged.

5. **Spend is the same as for every other stage.** Each call reserves against the run's budget through the stage's
   `SpendGuard` and is journaled, so a stage with 30 chapters cannot pass the cap and its cost survives a crash.

6. **The stage's own artifact is `draft.md`**, an index of the chapters drafted and their lengths, so that the stage
   leaves the same kind of trace as the others and later stages can name one input.

## Not decided here

The fact tracker, structural and line revision, copy edit, front and back matter, assembly into `books/<slug>.toml`
and claim verification are separate slices, each recorded by an amendment when it is built.

**Parallel drafting.** If it is wanted after 1.0, a join counter would slot in as follows: the `draft` stage would
enqueue one `run.draft_chapter` message per chapter and finish when an atomic counter row reaches the chapter count.
It is not built because chapters drafted at the same time cannot see each other's summaries, so continuity would rest
on the outline alone, and because it adds a queue message, a table and a worker-sharing rule for the spend guard
(which today is per process) for a speed-up that a first book does not need.

## Consequences

- **The plan's fan-out, join counter and concurrency cap are dropped for 1.0.** That is a deliberate change to
  the plan, recorded here.
- A book takes as long as its chapters take in a row. The stage is long-running, so it must stay within the queue's
  redelivery window; the next slice records how long, and a person can resume a run that was stopped.
- The outline's format is now a contract between two stages: changing the `stage_outline` template or the parser means
  changing both, with a version bump and a new fixture.
- A run whose outline stage produced a malformed outline fails with `OUTLINE_INVALID`, and, because the journal
  replays the same request, trying the same stage again with the same prompt gives the same answer. The remedy is to
  change what the outline stage is asked (for example with a skill) and start a new run.

## Amendment: the drafting stage as built (2026-11-22)

`DraftStageExecutor` does the stage, and `StageExecutorRouter` sends `draft` to it and every other stage to
`ModelStageExecutor`. The plan names `draft` after `outline`, but there is no recipe for it, because it is not one
prompt. What the code does where this decision left room:

- **A chapter written but not summarized is summarized from its stored text, never redrafted.** "Done" is both files,
  but the two calls are separate, so a stage that fails between them resumes at the summary alone.
- **How long a chapter is.** The brief's `target_words` shared across the chapters, or 2,500 words when there is none,
  never under 300 or over 6,000. The output cap is that many words as tokens (1.6 a word) plus 400, never more than the
  model allows. The input budget is the model's window less the output cap, less a 512-token margin, less an estimate
  for any skills enabled for the stage. A window too small for that stops the stage before the first call
  (`STAGE_MODEL_TOO_SMALL`).
- **The instruction holds numbers only.** The only plain text in the draft prompt says which chapter of how many and
  about how many words; the voice, the grounding, the beats, the summaries and the tail are untrusted blocks, as
  the context assembler lays them out.
- **A call that does not finish stores nothing for that chapter** and fails the stage (`STAGE_ANSWER_UNUSABLE`,
  with the model's own reasons); the chapters before it stay, and the next delivery starts at that chapter.
- **The summary of a chapter is a short note** (400 tokens at most) from `stage_summary`; the draft prompt gets each
  one on one line as `Chapter k: ...`, oldest dropped first when the window is short.
- **Not yet checked:** that a chapter keeps to its beats or its length. That belongs to revision. Nothing here has run
  against a live model.

## Amendment: the assemble stage (2026-11-22)

A non-fiction plan now ends with `assemble`, which makes no model call. `AssembleStageExecutor` reads `outline.md` and the
`chapter_NN.md` files and writes, in the run's artifacts, the project layout `BookLoader` reads:
`manuscript/src/chapter_NN.md` and `manuscript/books/<slug>.toml`, plus `assemble.md` listing them. A property test
holds the contract: whatever a model wrote, the stage either refuses with `MANUSCRIPT_TEXT_REFUSED` or writes a manuscript that
`BookLoader` loads in strict mode and the forbidden-content check passes.

- **Dashes are rewritten, unfinished work is refused.** The typesetter refuses an em or en dash in non-fiction, and a
  model's prose is full of them, so a dash between digits becomes a hyphen and any other dash becomes a comma (or nothing
  at the start or end of a line or before punctuation). A marker such as `[TODO]`, or the word `Draft`, is refused with
  the chapter and line, because deleting it would hide an unfinished chapter. The rewrite is a plain edit; the copy edit
  stage is where the sentences get reworked.
- **The outline's title heads the chapter.** A heading the model put at the top of its answer is dropped, and any other
  level-1 heading in the body becomes level 2.
- **Nothing is written until every chapter has been cleaned**, so a refused chapter leaves no half manuscript.
- **The config holds only what is known:** the kind, the title (the brief's hint, or its idea's first line), `src`, the trim
  size when the brief set one, and one part, `Part One`, holding every chapter. It has no author, publisher, edition, year or
  bio. Those are the author's, so the book loads but does not build until they are added. Setting them, and real parts,
  front and back matter belong to the front/back matter and metadata slice.

## Amendment: the listing and the author's details (2026-11-22)

A non-fiction plan now has a `metadata` stage after `outline` (before drafting, because it needs only the brief, the positioning and the
outline), and `assemble` reads its result.

- **`metadata` is one prompt**, so it has a recipe and goes through the same executor as the earlier stages. It writes the title, subtitle,
  description, seven keywords and one to three categories in a fixed format. `MetadataParser` reads it strictly and
  `NonfictionOutputChecks` refuses an unreadable one before it is stored (`METADATA_INVALID`). `BookMetadata` holds the release contract's rules
  (an 80 word description of at most 4,000 characters, seven distinct keywords, one to three browse paths of two levels or more), so a
  listing that is built cannot fail the contract for its shape.
- **The author's details are not a stage.** They are the author's, so they come from a file the person names with `EI_AUTHOR_PROFILE`
  (`AuthorProfile`, read by `TomlAuthorProfileLoader`), never from a model and never into a prompt. The assemble stage writes them into the
  config with the listing, with the release contract's `[release]` keywords and categories. A book assembled with a profile
  passes the release contract's metadata and category checks (a test runs them). Without one, it loads but does not build.
- **Front and back matter are not Markdown files.** The title page, copyright page, dedication and about-the-author page are made by the typesetter from the
  config, so no stage writes them. Pricing and the cover are still the author's to supply.
- **The title is the listing's**, which is the title the brief asked for when it gave one, and the config's file name is its slug.

## Amendment: the audit stage (2026-11-22)

A non-fiction plan now ends with `audit`, which makes no model call. `AuditStageExecutor` reads the `manuscript/` files, gives them to a
`ManuscriptAuditorInterface` as a project, and stores what comes back under `audit/` (`manuscript-audit.json`, `release-readiness.json`,
`publication-report.json`) with a summary in `audit.md`.

- **It runs the publishing pipeline's own audit-only gates**, the manuscript audit and the release readiness check, so there is one
  definition of a book that is ready. They need no TeX toolchain and no cover. `TempProjectManuscriptAuditor` lays the files out as a project in a
  private temporary folder, runs `PublishPipeline.publish(..., audit_only=True)`, reads the reports back and removes the folder; nothing of
  the book is left on disk. The publishing libraries are imported only when an audit runs.
- **Errors stop the run, warnings do not.** The reports are stored first, so a failed book can be read, then the run stops with `AUDIT_FAILED`
  and every error. A book with no prices passes with a warning for each, because prices are the author's.
- **Measured, not assumed:** an assembled book passes the real audit. Without an author profile the only extra finding is `missing-author`
  (a warning); with one, the findings are the missing prices and their date and source. A runtime test runs the real gates on a book
  that the assemble stage made.
- **Not done:** the PDF and EPUB build and the cover, which need the TeX toolchain, the cover design settings and cover art that are the
  author's. They are the next slice.

## Amendment: the editing passes (2026-11-22)

A non-fiction plan now has three editing stages between `draft` and `assemble`: `revise_structure`, `revise_lines` and `copy_edit`, each a
`RevisionStageExecutor` run with one of the passes in `NonfictionRevisionPasses`. Each is one call with no tools for each chapter, in order.

- **Each pass reads what the one before wrote.** The first reads `chapter_NN.md`; the files are `structure_NN.md`, `lines_NN.md` and
  `copy_NN.md`; and `assemble` now reads `copy_NN.md`. Each pass is told only what it needs: structure sees the whole outline, a line
  on every other chapter and this chapter's plan; lines sees the voice; copy sees nothing but the chapter. They have their own templates
  rather than the drafting assembler, whose system text says "write the chapter" and has no place for text to be revised.
- **A revision is kept only if it is plausible.** An answer that did not finish stops the stage, as in drafting. One that did finish but is blank, or whose
  length in words is outside the pass's bounds of the chapter's (a fifth for structure, a tenth for lines, a twentieth for copy), is **not stored and
  the chapter passes through unchanged**. A retry would replay the same answer, so stopping would only fail the run again. The stage
  reports each unchanged chapter as a tolerated issue (`revision-unchanged`), worked out from the stored files so a redelivery says the same,
  and `<stage>.md` lists every chapter's length before and after. This is a guard against an answer that is not an edit, not a judgment of
  whether an edit is good.
- **The window is checked, not assumed.** A chapter whose prompt (estimated at three characters a token) and answer would not fit the
  model's window stops the stage before the call (`STAGE_MODEL_TOO_SMALL`); nothing is cut to make it fit.
- **Cost:** every pass is one call per chapter, so a book with *n* chapters now makes about 5*n* model calls after the outline (a draft, a summary
  and three edits for each chapter). Every call reserves against the run's budget, and a run whose cap cannot cover the next call stops there.
- **Not known:** whether the edits improve the prose. Nothing here has run against a live model, and the length bounds only catch an answer
  that is plainly not an edit.

## Amendment: chapters are drafted one section per beat (2026-11-25)

A non-fiction chapter is no longer one model call. `DraftStageExecutor` writes it as one call per outline beat, each
section stored as `chapter_NN_sKK.md`, then joins the sections under `# Chapter N: Title` into `chapter_NN.md`. The reason
is the local model: a single reply was capped at 8,192 tokens and the model ended its chapters at 1,300 to 2,800 words,
so a 100,000-word book came out at 15,479 words.

- **Sections, not chapters, are the unit of resume.** A section that is stored is never redrafted; a chapter is done when
  its joined file and its summary exist, as before.
- **Each section sees the end of the one before it.** Section *k* gets section *k-1* as its previous tail (chapter *n-1*
  for section 1), the full chapter beats, and the earlier chapter summaries. The instruction holds numbers only.
- **The model writes no heading.** `context_pack` is version 3; the executor adds the chapter heading to section 1.
- **Length.** A chapter's share of the target is the brief's `target_words` over the chapters (2,500 when there is none),
  never under 300 or over 12,000. Each section is that share over the chapter's beats, never under 150 or over 3,000
  words, so one reply stays inside the output cap.
- **Novels are unchanged.** `DraftRecipe.sectioned` is false for novels, so they still draft a chapter in one call.

Not yet checked: that a section keeps to its beat, that a refusal is caught, and that a chapter reaches its length. Those
belong to the refusal and outline-sizing slices (PR 2 and PR 3 of the plan). Nothing here has run against a live model.

## Amendment: fitting a prompt does not use the spend count (2026-11-26)

`ContextAssembler` fitted prompts with the model's `count_tokens`, which for the local model is the UTF-8 byte count:
a deliberate upper bound for spend reservations, but about four times the real token count of English prose. A 30-chapter
outline (about 36 KB) alone overflowed the window, so drafting stopped at chapter 1.

- **Fitting uses its own estimate.** `FittingModel` wraps the model for the assembler only: everything is delegated, and
  the token count is characters divided by three, rounded up. Three characters a token is generous for English prose, so
  a fitted prompt still fits the window.
- **Reservation is unchanged.** `CallModel` still reserves with the wrapped model's own count, so spend stays bounded.
- **Each section sees the chapter titles, not the whole outline.** The grounding labels the list "The chapter titles" and
  holds one heading a line; the section's own beats come from the chapter's entry, as before. Novels get the same grounding.
- **Summaries may be longer.** The summary call is capped at 1,000 tokens, since reasoning counts against the cap.
- **The model request timeout is 1,800 seconds**, up from 600, so a long section on a slow laptop is not cut off.

Not yet done: a configurable timeout (it is a constructor default only), and the outline and editing passes, which are the
next slices of the plan.
