# Asking a model

A stage never talks to a provider directly. It goes through two services, one above the other.

## `CallModel`: one call, at most once

1. A request already answered **in this run and stage** is replayed from the run journal for nothing.
2. Otherwise the worst-case cost is reserved from the run's `SpendGuard` before anything is sent. A
   call that does not fit raises `BudgetExceededError` having sent nothing.
3. The call is made. If it raises, the reservation is released and nothing is journaled.
4. The answer is journaled with its real cost before the reservation is settled.

A replay is always a *complete* answer. A cut-off or declined answer is journaled too, because it was
billed, but under a key that includes the outcome and the attempt, so it is never mistaken for a good one.

## `AskModel`: what to do when the answer is not complete

A stage calls `AskModel.ask(guard, run_id, stage, attempt, request)` and gets a `ModelAnswer`: the text,
whether it is `complete`, the `issues` if it is not, and what it cost.

| What happened | What `AskModel` does |
|---|---|
| The model finished | Returns the answer. |
| It hit its output cap | Asks again with the cap **doubled**, up to the model's own limit. At the limit there is nothing more to try. |
| It declined | Asks the **identical** request again, up to `refusal_retries` times (default 1). |
| It runs out of attempts (default 4 calls in all) | Returns the best text it has and one **blocking** `QualityIssue` per defect: `TRUNCATED` (the text ends part-way) and/or `REFUSED` (the model's own words, trimmed to one line of 300 characters). The stage carries on. |
| The run is out of money, or the provider is down or at capacity | Nothing is caught here. `BudgetExceededError`, `TransientStageError` and `CapacityExhaustedError` go to the run, which retries or parks it. |

- **A refusal is never reworded, pressed or disguised.** It is the model's decision; a retry only covers a
  refusal that was a fluke. If it keeps declining, the stage gets no text and a `REFUSED` issue, and decides
  what to do (a later stage can step down a `DegradeLadder`, or the run records the section as missing).
- **Both issues are blocking**, so `--strict-release` refuses a book with a cut-off or missing section.
  An autonomous run still finishes and says what is wrong.
- **A resumed run does not pay twice.** Before any live call, `AskModel` looks for a complete answer at
  every output cap it could have reached, so a run that already has its answer replays it for nothing,
  without re-paying the cut-off attempts that led to it. An incomplete answer is never replayed: a resume
  tries again.
- **Every call is counted.** Each live call is journaled under `attempt * max_attempts + i`, so a stage's own
  retries and these attempts never share a journal key and no cost is lost.
- The issue detail quotes the model's own words, so treat it as untrusted text wherever it is shown.
