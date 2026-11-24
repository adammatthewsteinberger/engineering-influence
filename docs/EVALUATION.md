# The evaluation

ADR 0003 defines 1.0 by criteria that can be measured. Two of them are measured by one command, `ei evaluate`:

- **A5** — the pre-flight cost estimate is within 30% of what the books really cost.
- **A6** — a judge's mean score is at least 3.5 of 5 on every rubric dimension, and no dimension falls by more than 0.2 from the previous release.

`ei evaluate` makes every book of a fixed set with the stack's own pipeline, has a separately configured model score each finished book, and applies the bar. **It spends real money**, on the writing model and on the judge.

**Status.** The harness is built and tested against scripted models. It has not been run against a real model, so nothing here says the stack clears the bar. The first paid run is what produces the first baseline.

## What is in `evaluation/`

| File | What it is |
|---|---|
| `evaluation/set.toml` | The books made on every release: three non-fiction ideas and two novels, each a short book (`target_words = 10000`) so a run stays affordable |
| `evaluation/rubric.toml` | The dimensions, the question the judge asks for each, what a 1, a 3 and a 5 look like, which kinds of book each applies to, and the bar (`pass_mean = 3.5`, `max_drop = 0.2`) |

The set is the benchmark. Changing an idea changes what is measured, so edit the set only together with a new baseline. The ideas are generic on purpose: this repository holds no author's own material.

## Running it

```bash
EI_ALLOW_PAID=1 \
EI_STAGE_EXECUTOR=model EI_STAGE_MODEL_PROFILE=writer \
EI_EVAL_JUDGE_PROFILE=judge \
EI_MODEL_PROFILES=profiles.toml EI_MODEL_CATALOG=catalog.toml \
EI_AUTHOR_PROFILE=author.toml \
ei evaluate --out eval-out --budget-usd 5 --judge-budget-usd 3 --baseline previous/evaluation.json
```

- `EI_ALLOW_PAID=1` is required. Without it the command refuses before it reads a file or calls a model.
- `--budget-usd` is the most **each book** may spend; `--judge-budget-usd` is the most the **judge may spend in all**. Both are required and have no default.
- `--out` must be a new or empty folder, so one evaluation never mixes with another. Each book is made under it (`<case>/` and `<case>.state/`), and `evaluation.json` is written beside them.
- `--baseline` is an earlier `evaluation.json`. Without one only the pass mark applies; with one a fall of more than 0.2 on any dimension fails.
- The books are built for real, so the worker needs the TeX toolchain: run it from the `worker-tex` image ([WORKER_IMAGE.md](WORKER_IMAGE.md)).

Exit status: `0` the release meets the bar, `1` it does not (every reason is printed and is in the report), `2` the command could not run.

## The judge

The judge is a different configuration from the writer: `EI_EVAL_JUDGE_PROFILE` names a profile in the same `EI_MODEL_PROFILES` file, and the command refuses to start without it. A model that grades its own writing is the least informative judge, and pinning the judge's profile is what makes this release's scores and the last release's the same measurement.

- It is called once per finished book, with the whole book, using the `eval_judge` prompt ([PROMPTS.md](PROMPTS.md)). The book is an untrusted blank: a book that tells the judge to score it highly is data, not an instruction.
- It sees the text only: not the brief, what the run cost, or any earlier score.
- It answers one JSON object, a whole score from 1 to 5 and a reason for each dimension. An answer that is not exactly the rubric's dimensions with whole scores is refused (`JUDGE_ANSWER_INVALID`) and asked for once more; two refusals stop the evaluation, because scores from a judge that sometimes could not answer would not be comparable.
- It has a budget of its own, reserved call by call before anything is sent, so it cannot spend past `--judge-budget-usd`. A call that does not fit is refused (`JUDGE_BUDGET_EXHAUSTED`).
- A book too long for the judge's window is refused (`JUDGE_INPUT_TOO_LARGE`), not cut: a judge that read half a book scores half a book.

## The bar

A release meets the bar when none of these is found. Each one that is found is listed in `evaluation.json` and printed.

1. **Every book finished.** A book whose run failed, stopped for money or did not build is a failure of the release, not a missing data point: leaving it out would let a pipeline that breaks on hard ideas pass by scoring only the easy ones. Only a finished book is judged.
2. **Every dimension's mean reaches the pass mark.** The mean is over the books the dimension applies to (`kinds` in the rubric).
3. **No dimension fell by more than the allowed drop** since the baseline. A dimension the baseline had and this evaluation did not measure is a failure.
4. **The cost estimate was within 30% of what was spent**, over the whole set. Money spent with no estimate recorded is a failure, because the check cannot be made.

## The report

`evaluation.json` is stable (the same inputs give the same bytes) and is its own baseline: commit it, and pass it as `--baseline` to the next release's evaluation. It holds the rubric version and bar, `dimension_means`, the spend (making, estimated, the estimate's error, judging), the verdict, and for each case the title, the run's status, how many chapters and words, what it cost, and every score with its reason. Read the reasons: a mean says how far, not why.

## What it does not tell you

- It cannot show that a real model clears 3.5. Only a paid run can.
- A judge is a model. Its scores are comparable from release to release only while the judge's profile and the rubric stay the same; change either and take a new baseline.
- The estimate's tolerance is measured on five short books. The estimator's constants are first guesses until real runs calibrate them.
- Five books are a small sample. A pass is evidence, not a guarantee.

## Nightly

`.github/workflows/nightly-eval.yml` runs the evaluation each night. It is **off** until the repository variable `RUN_NIGHTLY_EVAL` is `true`, and it runs in the `evaluation` environment, which holds the model key and whose reviewers approve each run. It has not run yet. The maintainer provides the secrets, the profiles and the committed baseline; see the comments in the workflow.
