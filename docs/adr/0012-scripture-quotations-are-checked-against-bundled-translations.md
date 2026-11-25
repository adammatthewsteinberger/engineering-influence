# 0012: Scripture quotations are checked against bundled public-domain translations

## Status

Accepted, 2026-11-25.

## Context

A book on faith quotes Scripture, and a model writes those quotations from memory. A quotation that is almost right
(a word changed, a clause merged) or a paraphrase set in quotation marks is the commonest error, and it is the error a
reader of a Christian book notices first. The run had no way to catch it.

## Decision

- **Six translations ship with the product**, as offline data: the King James Version, the World English Bible, the
  American Standard Version, Young's Literal Translation, the Douay-Rheims 1899 and the Berean Standard Bible. Each is
  catalogued as public domain by eBible.org, from which the archives were taken. `SOURCES.md` records each archive's
  SHA-256, and `scripts/scripture/build_bundle.py` rebuilds the files byte for byte.
- **A quotation is a passage of at least four words in quotation marks, followed within 40 characters by a citation.**
  The citation is parsed (`ReferenceParser`) into verses, and the quotation is compared with those verses in every
  translation that has them, ignoring case, punctuation and typography.
- **Four verdicts, all non-blocking.** Word for word in some translation: right, nothing reported. At least 90% of its
  words in order in a translation: `SCRIPTURE_NEAR`, naming the closest translation. Otherwise: `SCRIPTURE_MISQUOTED`.
  When no translation has the verses at all: `SCRIPTURE_UNCHECKED`.
- **The check runs on each drafted non-fiction chapter**, as the drafting stage's checks. Findings are issues in the
  stage report; they do not stop the run, because a human reads the book and the author decides.

## Consequences

- The Douay-Rheims follows the Vulgate's versification, and its psalm titles sit inside verse 1. A quotation of a
  Psalm is checked against every translation, so the Douay numbering does not produce false findings.
- The Berean Standard Bible and the American Standard Version leave out the sixteen passages that are in the King James
  only (for example Matthew 17:21). A quotation of one of them is checked against the translations that have it.
- Paraphrases that are not in quotation marks are not checked. Checking them against the BSB (the plan's "paraphrase
  against BSB") needs a judgement about meaning, not words, and is not part of this decision.
- The bundle is about 8 MB, shipped in the wheel and the sdist.
- Books of the deuterocanon are not parsed as references; the reference parser covers the 66 books of the Protestant
  canon.
