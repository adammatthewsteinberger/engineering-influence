# Novels

**BLUF:** `--kind novel` writes a novel in nine stages, from a brief to a built book. A novel has no research
stage and no built-in tools. Instead it has a story bible, a small set of facts (who, where, when) that every
chapter is checked against. Novels get no editing passes yet, so a novel is built from its draft as written.

A novel run is a different kind of book from a non-fiction one: it is not argued from sources, so it has no research
stage and no tools, and it has a story bible that every chapter must agree with. `BookKind.NOVEL` picks it, and the
runtime dispatches by kind, so a non-fiction run is untouched.

## Why a novel needs a bible

> **Daniel:** Chapter three says Mara is nineteen. Chapter eleven says she turned thirty last spring. Why do
> models do that?
>
> **Professor Feynman:** How does a television series with twelve writers keep a character's eye colour the same
> for nine years?
>
> **Daniel:** Someone keeps a document. The show bible. Everybody checks it.
>
> **Professor Feynman:** A chapter is drafted with limited memory of the others, so the same trick is used. Before
> any chapter exists, one stage writes the story bible: the characters with their ages, the places, the dated
> events, how many years the story spans. It is data, not prose.
>
> **Daniel:** And each chapter is given it.
>
> **Professor Feynman:** Given it, and then the whole draft is checked against it by a continuity checker that
> looks for a name, a place, an age or a date that does not match. Here is where the picture thins out: a human
> script editor would also fix the slip. This one reports it and the run carries on. A repair pass for continuity
> findings is not built, and neither are editing passes for novels.
>
> **Daniel:** So the bible prevents most slips, the checker finds the rest, and fixing them is still my job for
> now.

## What is built

| Stage | Prompt | What it writes | Checked when written |
|---|---|---|---|
| `brief` | `novel_brief` | premise, genre and tone, point of view and tense, setting, characters, stakes, shape, length, content limits | not parsed |
| `story_bible` | `novel_story_bible` | one JSON object: premise, characters (name, aliases, age), places, dated events, span in years | read by `StoryBibleParser` (`STORY_BIBLE_INVALID`) |
| `beats` | `novel_beats` | 15 to 25 numbered beats in three acts, in story order | not parsed |
| `outline` | `novel_outline` | the chapters, in the same `## Chapter N: Title` format a non-fiction outline uses | read by `OutlineParser` (`OUTLINE_INVALID`) |
| `metadata` | `novel_metadata` | the store listing: title, subtitle, blurb, seven keywords, one to three categories | read by `MetadataParser` (`METADATA_INVALID`) |
| `draft` | `novel_context_pack`, `novel_summary` | each chapter in order, then a summary of it for the next; `chapter_NN.md`, `summary_NN.md`, `draft.md` | continuity, once every chapter is written |
| `assemble` | none (no model call) | the book as a project under `manuscript/`: `src/chapter_NN.md` and `books/<slug>.toml` with `kind = "novel"` | the chapters are cleaned and any unfinished marker or the word `Draft` is refused |
| `audit` | none | the same publish audits as `ei book audit` (`audit.md`, `audit/`) | a book that fails stops the run |
| `build` | none | the interior PDF, EPUB, covers, listing and KDP bundle under `book/`, the reports under `build/`, `quality-report.json` and `build.md` | a book that does not pass stops the run (`BUILD_FAILED`) |

The plan is nine stages, from the brief to a built book. Only the editing passes (revision and copy editing) are not
built, so a novel is built from the draft as written.

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

## Trying it

A novel run ends in a built book, as a non-fiction run does. The `metadata` stage comes right after the outline, so `assemble` can write the config
from the listing and the draft's own chapters. A novel keeps its em and en dashes (only non-fiction refuses them), and its
trim size is the brief's (`trim_size`, for example `5.5x8.5`). **There are no editing passes for a novel yet**: the book is built
from the draft as written, so it is only as good as the draft. The build needs the TeX worker image
([WORKER_IMAGE.md](WORKER_IMAGE.md)); `EI_BUILD_STRICT_RELEASE` works as for non-fiction ([BOOKS_AND_KDP.md](BOOKS_AND_KDP.md)).

`ei book create --kind novel "<idea>" --budget-usd N --out DIR --profile FILE` makes a novel the same way it makes a
non-fiction book ([INTERACTIONS.md](INTERACTIONS.md)). The paid smoke test in [LIVE_SMOKE_TEST.md](LIVE_SMOKE_TEST.md) drives only the
non-fiction plan. A novel has been run only against scripted servers, and that scripted run of the whole plan is built with the real
toolchain, including as a strict release (`tests/toolchain/test_run_builds_book.py`). To see the prompts a novel sends without a model, read the templates named in the table above
(`src/engineering_influence/infrastructure/prompt_library/templates/novel_*.toml`); each is versioned, and its text is
pinned in `tests/fixtures/prompt_templates.lock.toml`.

## What is not built or not checked

- Revision and copy editing for a novel; a repair pass that asks the model to fix a continuity finding.
- A paid check of the novel plan against a real model.
- Nothing here has been run against a real model. The prompts are tested against scripted servers, and how well a
  20-billion-parameter local model writes a story bible as valid JSON is not known: if it often does not, the run stops
  with `STORY_BIBLE_INVALID` and the message says why.
- Series bibles (one bible across several books).
