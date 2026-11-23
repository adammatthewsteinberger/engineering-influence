# Novels

A novel run is a different kind of book from a non-fiction one: it is not argued from sources, so it has no research
stage and no tools, and it has a story bible that every chapter must agree with. `BookKind.NOVEL` picks it, and the
runtime dispatches by kind, so a non-fiction run is untouched.

## What is built

| Stage | Prompt | What it writes | Checked when written |
|---|---|---|---|
| `brief` | `novel_brief` | premise, genre and tone, point of view and tense, setting, characters, stakes, shape, length, content limits | not parsed |
| `story_bible` | `novel_story_bible` | one JSON object: premise, characters (name, aliases, age), places, dated events, span in years | read by `StoryBibleParser` (`STORY_BIBLE_INVALID`) |
| `beats` | `novel_beats` | 15 to 25 numbered beats in three acts, in story order | not parsed |
| `outline` | `novel_outline` | the chapters, in the same `## Chapter N: Title` format a non-fiction outline uses | read by `OutlineParser` (`OUTLINE_INVALID`) |
| `draft` | `novel_context_pack`, `novel_summary` | each chapter in order, then a summary of it for the next; `chapter_NN.md`, `summary_NN.md`, `draft.md` | continuity, once every chapter is written |

The five stages are the whole plan today. The editing passes, assembly and the audit for a novel are not built, so a
novel run stops after the draft.

## Drafting

The drafting stage is the same loop non-fiction uses (ADR 0010): one chapter after another, each written from the
voice (the brief and the story bible), the grounding (the whole outline and the beats of the whole novel), this
chapter's entry, the summaries of the chapters before it and the tail of the last one, fitted to the model's window.
A `DraftRecipe` says what a kind of book reads and how it labels it, so the non-fiction prompt is byte-for-byte what it
was. The one plain-text instruction carries only numbers and the two content levels, and says that `not given` means
mild violence and sweet heat. A chapter is done when its text and its summary both exist, so a redelivered stage does
only what is left.

When every chapter is written, `NovelDraftChecks` reads the whole draft against the story bible with the continuity
checker. Each finding becomes one **non-blocking** quality issue on the run (`CONTINUITY_NAME`, `CONTINUITY_PLACE`,
`CONTINUITY_AGE`, `CONTINUITY_TIMELINE`), the run keeps going, and `continuity.md` lists every finding (the run records
the first 50). A finding is a question, not a verdict: a flashback, or a new character named like an old one, is a good
reason for one to be wrong, so nothing is stopped or rewritten automatically. Nothing repairs a chapter either; that
is for the author, or a later editing pass.

## Content levels

A brief may set `violence` (`none`, `mild`, `moderate`, `graphic`) and `heat` (`none`, `sweet`, `steamy`, `explicit`),
and only a novel may. Every novel stage first asks `ContentPolicy` whether the model is *recorded* as allowing those
levels, before any call is made: the ceiling is something you record in your own model catalog after reading your
provider's usage policy (`max_violence`, `max_heat`; see [MODEL_CATALOG.md](MODEL_CATALOG.md#content-levels)), and a model with
none recorded is held to `mild` and `sweet`. The levels also go into the prompts, so a stage is told to stay within them.
That is a guard against asking a model for what its provider says it will not write, not a content filter.

## The story bible and the continuity checker

`StoryBibleParser` reads the first JSON object in the stage's answer, so a preamble or a code fence does no harm.
Every text is collapsed to one line and stripped of control and invisible characters before the bible's own limits
apply, the timeline is sorted by its time values, and a value of the wrong type or a bible that breaks its own rules (a
name twice, more than 60 characters) stops the run where it was written, before drafting is paid for.

`ContinuityChecker` reads chapters against the bible with no model call and reports near-miss names and places, ages
outside the bible's range, and events mentioned out of order. The draft stage calls it once, over the whole draft.

## What is not built or not checked

- Revision, copy editing, assembly and the audit for a novel; the metadata and KDP listing for fiction; a repair pass that
  asks the model to fix a continuity finding.
- Nothing here has been run against a real model. The prompts are tested against scripted servers, and how well a
  20-billion-parameter local model writes a story bible as valid JSON is not known: if it often does not, the run stops
  with `STORY_BIBLE_INVALID` and the message says why.
- Series bibles (one bible across several books).
