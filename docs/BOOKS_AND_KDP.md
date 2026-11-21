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
| Listing metadata | Title, subtitle, author, description size, **exactly seven unique keywords** (categories are not checked yet) |
| Pricing | List-price policy, freshness and source of the inputs, estimated print cost and royalty |
| Manuscript quality | Forbidden-content, scaffold-leak, chapter-opening, contents, research-apparatus and formula checks |
| Evidence | A machine-readable release report with file digests, tool versions and git state |

A book is **release-ready** only when every audit passes. The report ends with
`human_review: pending`: a person signs off before anything is published.

## What is built, and what is not

Be exact about today's state (alpha `0.1.0a1`):

| | Status |
|---|---|
| Orchestration: queue, worker, ledger, gates, dead-letter, API, MCP, CLI, SDK, webhooks | Built and tested |
| KDP packaging and verification (`ei book …`): audits, PDF, EPUB, covers, QA, readiness report | Built, tested, used to build ten real books |
| **The writing itself** | **Not yet autonomous.** The runner and gate that ship are deterministic placeholders (`DeterministicRunner` returns fixed text). A model-backed runner and rubric gates implement the same interfaces and are the next milestone |
| Methodology stages (P1 to P14), autonomy modes, budget guards, automatic job retries | Not built |
| Uploading to KDP | Never automatic: KDP has no publishing API. You upload the verified files and paste the verified metadata yourself |

So today you can run the full orchestration end to end and produce KDP-ready packaging from
a manuscript; fully autonomous drafting arrives when a real runner is plugged into the
`RunnerInterface`. This page is updated as each row changes.

## Fiction and non-fiction

Both use the same stages and the same publish step. Non-fiction is bounded by its postulates
and research apparatus (claims need sources; the research check enforces it). Fiction adds the
`novel` and `screenplay` stages. Choose the stages in the request, for example
`["thesis", "book"]` or `["novel", "distribution", "publish"]`.

### Book kind and the text rules

A book's config (`books/<slug>.toml`) may say `kind = "novel"`; without it the book is
non-fiction. The kind picks the text rules the typesetter and the checks apply. An unknown kind
stops the build with a message naming the two valid ones.

| Rule | `nonfiction` (the default) | `novel` |
|---|---|---|
| Em dash (`—`) in the text | Refused, in the manuscript, the PDF and the EPUB | Allowed |
| En dash (`–`) | Refused | Refused |
| A `---` line inside a chapter | Prints nothing | Prints a scene break: a centred `* * *`, and the next paragraph is not indented. A rule that opens or ends a passage, sits beside another rule, or is inside a quote or list prints nothing |
| The word `Draft` | Refused anywhere | Refused in narration; allowed inside curly quotation marks, so a character may say it |
| Unfinished markers such as `[TODO]` | Refused | Refused |

A quoted span for the `Draft` rule is at most 500 characters, so an opening quote that never
closes cannot hide a stray `Draft` later in the text. Narration that legitimately starts a
sentence with `Draft` still has to be reworded. `tests/fixtures/fixture_novel/` is a small novel
that shows each rule and is built with the real toolchain in CI.

### Trim size and paper

A book's config sets the page size and the interior paper. Both default to what every book used
before they existed, so a config that says nothing builds exactly the same files as before.

| `trim_size` | Page (in) | Hardcover |
|---|---|---|
| `6x9` (default) | 6 x 9 | yes |
| `5.5x8.5` | 5.5 x 8.5 | yes |
| `5x8` | 5 x 8 | **no**: KDP does not print a hardcover at this size |

| `paper` | Spine width per page |
|---|---|
| `white` (default) | 0.002252 in |
| `cream` | 0.0025 in |

The trim size sets the interior's page size (the PDF check refuses any other), the cover layouts
and the ebook cover's proportions. The paper sets the spine width of the paperback and hardcover
wraps, so a cream book's spine is wider than a white book's of the same length. An unknown value
stops the build with a message listing the valid ones.

A `5x8` book is paperback and ebook only. It gets no hardcover interior and no hardcover wrap, a
`[formats] hardcover = true` or `release.formats.kdp_hardcover = true` is refused, and its
`[release.pricing]` needs no hardcover price. If you add one anyway it is still checked, and
selling a hardcover through another provider still needs `hardcover_provider` as before. The
hardcover column follows KDP's published hardcover sizes as I understand them today; KDP changes
what it offers, so confirm against its current list before relying on it.

## Where to go next

[Getting started](GETTING_STARTED.md) · [Interfaces](INTERACTIONS.md) ·
[Architecture](ARCHITECTURE.md) · [Configuration](CONFIGURATION.md)
