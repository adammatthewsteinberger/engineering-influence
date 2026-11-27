# ADR 0003: Definition of 1.0

Status: accepted

## Context

The package is alpha (`0.1.0a1`). The orchestration and the KDP packaging are built, but the
writing is not: the runner and gate are deterministic placeholders, nothing carries a book's
brief to the worker, stage output is discarded, and no command turns an idea into files. The
vibey standards define no "stable" bar, so this ADR sets one.

## Decision

1.0.0 ships only when every criterion below holds, with the stated evidence.

| # | Criterion | Evidence |
|---|---|---|
| A1 | `ei book create --kind nonfiction "<idea>"` and `--kind novel "<idea>"` each produce, with nobody in the loop, an interior PDF, an EPUB, an ebook cover, a paperback wrap, `listing.md`, `publication-report.json` and `quality-report.json` | Two archived dogfood runs |
| A2 | Those files pass `ei book publish --strict-release` with epubcheck required and real LuaLaTeX | CI `toolchain` job, dogfood logs |
| A3 | Both books load in Kindle Previewer and KDP's print previewer without errors | Manual check, screenshots in the release PR |
| A4 | A run killed at any stage resumes to the same end state without paying for finished stages again | Chaos and resume tests |
| A5 | No run exceeds its budget cap; the pre-flight estimate is within 30% of actual spend on the evaluation set | Property test, evaluation report |
| A6 | Mean rubric score is at least 3.5 of 5 on every dimension and falls no more than 0.2 from the previous release | Nightly paid evaluation |
| A7 | These contracts are frozen and snapshot-tested: the brief and book-config schemas, the REST OpenAPI document, the webhook catalogue, the job message, the CLI, the SDK and the MCP tools | Snapshot tests, `docs/COMPATIBILITY.md` |
| A8 | Every quality gate in `CONTRIBUTING.md` passes, including 100% line and branch coverage of the core and the SDK, enforced as one global threshold | CI |
| A9 | Core and SDK are published to PyPI in lockstep, and images to GHCR, with attestations | Release run, `gh attestation verify` |
| A10 | Every documented claim matches the code, and a threat model exists | Documentation and release audits |

The run is autonomous: it never waits for a person. A bounded revision loop that runs out keeps the
best version and records the problem in `quality-report.json`. A budget planner reserves the cost
of finishing the book before it spends on revisions, so a run always completes. Uploading to KDP
stays manual, because KDP has no API.

Scope at 1.0 is non-fiction and novels. The screenplay, hub, spokes and distribution stages are
experimental and outside the stable contract.

## Consequences

- Each milestone toward 1.0 maps to a pre-release (alpha, beta, release candidate, see ADR 0004).
- The 1.0.0 release commit sets the version by hand, as every release does (ADR 0005). Conventional
  commits with `BREAKING CHANGE:` footers are still required, but they do not choose the version.
- Paid model runs, publishing and the KDP upload need the maintainer's explicit go-ahead.

Amended by ADR 0017: a `screenplay` book kind is added as an automated kind, and its plan has now landed. Screenplay runs are outside the 1.0 criteria A1 to A8, which cover non-fiction and novels only; the scope statement above is otherwise unchanged. Adding screenplays to 1.0 would need its own criteria and evidence.
