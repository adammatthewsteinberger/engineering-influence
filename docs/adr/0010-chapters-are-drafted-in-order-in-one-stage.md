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

3. **Each chapter is drafted from what came before it** (to be built in the next slice). For chapter *n* the
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
