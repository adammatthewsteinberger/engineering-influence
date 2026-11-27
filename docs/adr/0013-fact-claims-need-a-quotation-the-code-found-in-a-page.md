# 0013: A factual claim is supported only by a quotation the code found in a page it read

Status: accepted, 2026-11-25.

## Context

A non-fiction book states facts: statistics, dates, what a study found. A model asked whether a source supports a claim
will often say yes about a page it did not really read, or quote words the page never contained. A check that trusts
the model's yes is no check.

## Decision

- **The code searches and reads; the model only judges.** The fact-check stage runs after copy editing. For each
  chapter a model lists at most eight checkable claims, each with a search query. The code runs the search (through the
  same provider the research stage uses) and fetches up to two pages per claim. The model is then asked, once per page,
  whether that page supports the claim and for the words that do.
- **A claim is supported only when the model names a quotation and the code finds it in the fetched page**, word for word,
  with runs of whitespace treated alike. A yes without a quotation, a quotation not in the page, or an unreadable answer
  is not support.
- **A claim that every readable page fails to support is softened or removed**, by one call that changes only those
  sentences. The rewrite is kept only if it is within a tenth of the chapter's length and was not cut off; otherwise the
  chapter is kept and the claim is reported as unresolved.
- **A claim that could not be searched or read is unchecked**, and it is left as written. A failed search is not evidence
  that a claim is false.
- **Every outcome is recorded** in `fact_check.json` and each finding is a non-blocking issue in the stage report, so
  `quality-report.json` lists it.

## Consequences

- The check is only as good as the sources the search finds. A claim with no page on the web is unchecked, not false.
- Bible quotations are not claims for this stage; they are checked by the Scripture check (ADR 0012).
- Budget runs out the way it does for the editing passes: the chapters that are not checked are kept as written and
  reported as skipped.
