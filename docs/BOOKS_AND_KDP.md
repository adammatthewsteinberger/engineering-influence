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
| Non-fiction stages | Started: brief, positioning and outline can be done by a model (`EI_STAGE_EXECUTOR=model`), never yet run against a live provider. Research, drafting, revision, copy edit, front and back matter and assembly are not built |
| Methodology stages (P1 to P14), autonomy modes | Not built |
| Budget caps, and retry of a run's transient stage failures | Built and tested, but not yet exercised by a live model run |
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

### Listing metadata

The release contract (`[release]` in the book's config) is checked before anything is built.
Beyond the title, subtitle and author, it covers the listing:

| Setting | Rule | Finding |
|---|---|---|
| `description` (top level) | at least 80 words (`release.minimum_description_words`), at most 4,000 characters (`release.maximum_description_characters`, which can only lower KDP's limit in practice) | `description-too-short`, `description-too-long` |
| `release.keywords` | exactly seven, unique, none empty | `keyword-count`, `duplicate-keyword`, `empty-keyword` |
| `release.categories` | up to three Amazon browse paths such as `Books > Literature & Fiction > Mystery`; unique; at least two levels | `too-many-categories`, `category-not-a-path`, `duplicate-category`, `categories-invalid` |

Categories are Amazon's browse tree, not BISAC subject codes (`FIC009000`), which are a different
scheme: a BISAC code in `categories` is refused as `category-is-bisac`. The check cannot know
Amazon's tree, which changes and has no API. It checks the count, the shape and the uniqueness; you
confirm the names when you upload. A book with no categories gets the warning
`categories-not-declared`, never an error, so books written before this check keep passing a strict
release. The 4,000-character and three-category limits are KDP's published limits as I understand
them; confirm them against KDP's current help pages.

### The back cover and the barcode area

The back cover carries the description and the author note, and KDP keeps a 2 x 1.2 in area clear
for the barcode it adds. The description is set above that area, shrinking until it fits, down to a
smallest size. If it still does not fit, the build stops with `BackCoverTextTooLongError`, which
reports how many characters the description has, how many fit at this trim size and how far it
overflows, instead of drawing text into the barcode area. The limit on the cover is lower than
KDP's 4,000-character listing limit and depends on the trim size and the cover style: with the
default style, about 3,000 characters fit at 6x9 and 5.5x8.5 and about 2,200 at 5x8, and the error
gives the exact figure for your book. Text, and any ink, in the barcode area is also caught after
rendering, at every trim size, for the paperback and the hardcover.

### What the typesetter refuses

Text that reaches TeX may be written by a model, so the typesetter escapes it and refuses a few
things it cannot make safe (the full picture is in [THREAT_MODEL.md](THREAT_MODEL.md)):

- A **code block that contains `\end{verbatim}`** stops the build with a message, because TeX would
  end the code environment there and read the rest of the line as TeX.
- A **`website` that is not an http or https address** stops the build: write `https://pub.example`
  or a bare host name such as `pub.example`. Another scheme (`javascript:`, `data:`), a space, or a
  `host:port` is refused; write a port with its scheme (`https://pub.example:8080`).
- Any URL, including a `website` and an `email`, is printed with every character outside the
  ordinary URL set percent-encoded, so a space, a quote or an accented letter appears as `%20`, `%22`
  or `%C3%A9`.
- An **ebook title** with any of `& < > " # % \ { } ~ ^ $ _` is refused.
- The title, subtitle, author and edition also go into the PDF's metadata, where the characters
  `\ { } % # ^ ~`, control characters and unbalanced parentheses are dropped. An ordinary title,
  including balanced parentheses, is unchanged.

### A build that runs too long, or uses too much

Each build tool has limits, and a tool that passes one is stopped, together with everything it started:

| Tool | Time | Memory | Disk written |
|---|---|---|---|
| `latexmk` and `tex4ebook` | 30 minutes | 8 GiB | 4 GiB |
| `epubcheck` | 10 minutes | 4 GiB | not measured |
| the page renderer | 10 minutes | 2 GiB | 4 GiB |

Memory is the resident size of the tool and everything it started. Disk is the size of the directory it
writes into. The build then fails with a message such as
`latexmk did not finish within 1800 seconds and was stopped`,
`latexmk used 8300 MiB of memory, over its limit of 8192 MiB and was stopped` or
`latexmk wrote 4300 MiB to disk, over its limit of 4096 MiB and was stopped`, followed by the tool's last
output so you can see where it stopped. Memory and disk are checked twice a second, so the figure in the
message can be a little over the limit. A normal book is far below all of these (the fixture books peak
at about 400 MiB). The limits are fixed in the code, not settings, and a book that legitimately needs
more than this is not supported yet.

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
