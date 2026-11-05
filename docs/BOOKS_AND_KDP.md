# From postulates to a KDP-ready book

**engineering-influence exists to write complete books, fiction and non-fiction, fully
autonomously, and to hand you a package that is ready to upload to Amazon KDP.** Everything
else in this repository (the API, MCP server, CLI, SDK, webhooks, queue and ledger) is the
machinery that makes that run unattended, recoverably and auditably.

You supply a project: a title, governing postulates (the claims and limits the book must
stay inside) and the stages to run. The pipeline does the rest.

```text
postulates ─▶ thesis ─▶ book | novel | screenplay ─▶ hub ─▶ spokes ─▶ distribution ─▶ publish
                              │
                              └─ each stage: runner writes · gate accepts or rejects · ledger records
publish stage ─▶ audit · interior PDF · EPUB · covers · page QA · release-readiness report
```

## What "KDP-ready" means here

The publish stage (`ei book publish`) produces, and verifies, the files and decisions KDP asks for:

| KDP requirement | What the toolchain does |
|---|---|
| Paperback interior | 6 × 9 in PDF typeset with LaTeX; margins and the page-count-dependent gutter checked against KDP's table; fonts embedded; page count against KDP's limits |
| Hardcover interior | Compact hardcover build; page limit checked, or an explicit external-provider decision required |
| eBook | EPUB built and validated (structure, links, `epubcheck`) |
| Covers | Front, back and spine/wrap for print at the exact trim and page count, plus the eBook cover; image, quiet-zone and layout checks |
| Listing metadata | Title, subtitle, author, description size, **exactly seven unique keywords**, categories |
| Pricing | List-price policy, freshness and source of the inputs, estimated print cost and royalty |
| Manuscript quality | Forbidden-content, scaffold-leak, chapter-opening, contents, research-apparatus and formula checks |
| Evidence | A machine-readable release report with file digests, tool versions and git state |

A book is **release-ready** only when every audit passes. The report ends with
`human_review: pending`: a person signs off before anything is published.

## What is built, and what is not

Be exact about today's state (alpha `0.1.0a1`):

| | Status |
|---|---|
| Orchestration: queue, worker, ledger, gates, retries, dead-letter, API, MCP, CLI, SDK, webhooks | Built and tested |
| KDP packaging and verification (`ei book …`): audits, PDF, EPUB, covers, QA, readiness report | Built, tested, used to build ten real books |
| **The writing itself** | **Not yet autonomous.** The runner and gate that ship are deterministic placeholders (`DeterministicRunner` returns fixed text). A model-backed runner and rubric gates implement the same ports and are the next milestone |
| Methodology stages (P1 to P14), autonomy modes and budget guards | Not built |
| Uploading to KDP | Never automatic: KDP has no publishing API. You upload the verified files and paste the verified metadata yourself |

So today you can run the full orchestration end to end and produce KDP-ready packaging from
a manuscript; fully autonomous drafting arrives when a real runner is plugged into the
`RunnerPort`. This page is updated as each row changes.

## Fiction and non-fiction

Both use the same stages and the same publish step. Non-fiction is bounded by its postulates
and research apparatus (claims need sources; the research check enforces it). Fiction adds the
`novel` and `screenplay` stages. Choose the stages in the request, for example
`["thesis", "book"]` or `["novel", "distribution", "publish"]`.

## Where to go next

[Getting started](GETTING_STARTED.md) · [Interfaces](INTERACTIONS.md) ·
[Architecture](ARCHITECTURE.md) · [Configuration](CONFIGURATION.md)
