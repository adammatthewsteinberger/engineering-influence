# Running a small book against a real model

**BLUF:** This is the smallest paid run that proves the whole chain against a real model: one short non-fiction
book, in one process, with a spending cap you set first. It never runs by default and will not start unless the
environment says you mean to spend. Until someone runs it, nothing in the writing pipeline has ever talked to a
live model.

Until this has been done, **nothing in the writing pipeline has ever talked to a live model**. Everything is tested against
scripted servers and fakes. This page is how you find out whether the prompts, the editing passes and the whole chain work
with a real one, and what it costs, with a limit you set in advance.

The test drives the whole non-fiction plan (brief, positioning, research, outline, metadata, draft, three editing
passes, assemble, audit, build) in one process, with no database, queue or worker. It writes every artifact and a report to a
folder you can read. It is a `paid` test: it never runs by default, and it will not start unless you say in the
environment that you mean to spend.

## What a passing test does not prove

> **Daniel:** Ten thousand tests pass. Is that not proof the writing works?
>
> **Professor Feynman:** A flight simulator can pass every drill. What has never happened in it?
>
> **Daniel:** Real weather. Real air.
>
> **Professor Feynman:** Every test here flies against a scripted model that answers exactly as the test wrote.
> That proves the machinery: the stages, the budget, the resume. It cannot prove that a real model follows these
> prompts, or what a book really costs.
>
> **Daniel:** So this test is the first real flight. Why is it so hedged about?
>
> **Professor Feynman:** Because it spends your money. You set the cap before it starts, it refuses to run without
> an explicit yes in the environment, and it writes down what it spent. And mind the limit even of a real flight:
> one short book on one model on one day. A pass means the chain holds together, not that the books are good.
>
> **Daniel:** Scripted tests prove the machine, this proves the chain, and neither proves quality. That is what
> the evaluation is for.

## What it spends, and what stops it

- **A cap you must set.** `EI_SMOKE_BUDGET_MICRO_USD` is the most the run may spend, in millionths of a dollar
  (`3000000` is three dollars). There is no default, on purpose; a run without one does not start.
- **A reservation before every call.** Each call reserves its worst case (its full output allowance at the model's
  price) against the cap, and a call that would pass the cap is refused before it is made. The run then stops at that stage and
  says so. So the cap is a ceiling on what is spent, and a cap smaller than a few worst-case calls stops the run early.
- **The size of the book.** `EI_SMOKE_TARGET_WORDS` (default 1,200) shapes the brief, and the outline decides how many
  chapters there are. Each chapter costs about five calls: a draft, a summary and three edits. A short target keeps it
  small, but the number of chapters is the model's choice, so the cap is what actually bounds the cost.
- **A made-up author.** The run always uses a fictional author profile. It never reads yours.

## What you need

1. A model profile and a price catalog for the model you want to test ([MODEL_PROFILES.md](MODEL_PROFILES.md),
   [MODEL_CATALOG.md](MODEL_CATALOG.md)), and the key in the environment variable the profile names. Check them first, which
   sends nothing: `ei doctor --models`.
2. A web search for the research stage: `EI_SEARXNG_URL` (a SearXNG instance) or `BRAVE_SEARCH_API_KEY`
   ([CONFIGURATION.md](CONFIGURATION.md), [RESEARCH.md](RESEARCH.md)). Without one the run stops at start with a clear message, before any
   call. Check that it answers first, which sends one search per provider and asks no model anything: `ei doctor --search`.
3. A dev install with the extras the audit and the runtime need: `uv sync --extra runtime --extra publishing`.
4. The TeX toolchain (`latexmk`, `lualatex`, `tex4ebook`, `zip`, and `pdftoppm` or `mutool`; `epubcheck` is optional
   unless the release is strict; `ei doctor --ready` checks them all; [WORKER_IMAGE.md](WORKER_IMAGE.md)) for the
   last stage, `build`, which turns the run's book into a PDF, an EPUB and the KDP bundle. Without it every earlier stage
   still runs and is reported, and `build` fails naming the missing tool.

## Run it

```bash
EI_ALLOW_PAID=1 \
EI_SMOKE_PROFILE=hosted \
EI_MODEL_PROFILES=profiles.toml \
EI_MODEL_CATALOG=catalog.toml \
EI_SMOKE_BUDGET_MICRO_USD=3000000 \
EI_SMOKE_OUT=./smoke-out \
uv run pytest -m paid tests/paid
```

| Variable | |
|---|---|
| `EI_ALLOW_PAID` | must be exactly `1`, or the test fails before it starts |
| `EI_SMOKE_PROFILE` | the name of the profile to use |
| `EI_MODEL_PROFILES`, `EI_MODEL_CATALOG` | the two files |
| `EI_SMOKE_BUDGET_MICRO_USD` | the hard cap, required |
| `EI_SMOKE_TARGET_WORDS` | optional, default 1,200 |
| `EI_SMOKE_IDEA` | optional; the book's idea, default a short one about windowsill herbs |
| `EI_SMOKE_OUT` | optional; a folder that does not exist or is empty. Default: a temporary folder, printed at the end |

It prints each stage with its outcome, its cost and its time, then the folder. The folder is written **even when the run
fails**, so you can see how far it got.

## Novels are not in this test yet

The test above drives the non-fiction plan only. A novel run is brief, story bible, beats, outline, metadata, draft,
assemble, audit and build, with no editing passes (see [NOVELS.md](NOVELS.md)).
Pointing `EI_SMOKE_IDEA` at a novel would not make the test write a novel: the smoke harness always builds a non-fiction
brief and plan. So there is no paid novel check yet. A novel live check needs the paid harness to take a novel brief (the rehearsal driver already runs a novel plan). Until
then, a novel has only ever been run against scripted servers, and its first real-model run will be a manual one with `ei doctor --local` and the prompts.

## What to read afterwards

In the folder:

- `smoke-report.json`: the status, the spend against the cap, and each stage's outcome, attempts, cost and seconds.
- `outline.md`, `metadata.md`, `chapter_NN.md`, `copy_NN.md`: what each stage wrote. Read a draft chapter next to
  its `structure_NN`, `lines_NN` and `copy_NN` versions to judge whether the editing passes helped. The report's
  `revision-unchanged` issues name chapters an edit changed nothing in, and its `revision-rejected` issues name
  chapters whose edit was not kept, with the answer's word count and the bounds it missed.
- `audit.md` and `audit/`: the book's own audit. A made-up author passes it with warnings about prices.
- `manuscript/`: the book as a project (`books/<slug>.toml`, `src/chapter_NN.md`).
- `book/`: the built book: `<slug>.pdf`, `<slug>.epub`, the covers, `listing.md` and `MANIFEST.json`. `build/` holds the
  readiness reports and the tool logs, `quality-report.json` the status with a checksum for every file, and `build.md` a summary.

## What a pass does and does not show

A pass shows that the chain works with a real provider (the adapter, token counting, cost reservation, refusals, every
executor, the audit) and what it costs. It does **not** show that the prose is good or that the facts are right: there is no
claim checking yet, and the only automatic judgment of an edit is its length. Read the chapters yourself.

A failure is information. The usual ones: a stage whose answer is not in the format a program reads (the outline or the
listing), a model whose window is too small for a chapter (`STAGE_MODEL_TOO_SMALL`), or a cap that was too small.

## Without spending

`tests/unit/test_smoke_run.py` runs the same driver against a scripted local server. It is the free rehearsal, and it
runs in the normal suite. It proves the chain, the budget stop, the retry and the folder, and says nothing about a
real model's answers.
