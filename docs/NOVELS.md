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

The four stages are the whole plan today. Drafting, the editing passes, assembly and the audit for a novel are not built,
so a novel run stops after the outline; they are the next slice of the novel work.

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
outside the bible's range, and events mentioned out of order. Nothing calls it yet; drafting will, after each chapter.

## What is not built or not checked

- Drafting, revision, copy editing, assembly and the audit for a novel; the metadata and KDP listing for fiction.
- Nothing here has been run against a real model. The prompts are tested against scripted servers, and how well a
  20-billion-parameter local model writes a story bible as valid JSON is not known: if it often does not, the run stops
  with `STORY_BIBLE_INVALID` and the message says why.
- Series bibles (one bible across several books).
