# ADR 0017: A screenplay's source is a folder of files, read whole and pinned by digest

Status: accepted

## Context

ADR 0011 caps run inputs at 50,000 characters each and 200,000 in all, which is right for a brief and wrong for a novel:
a full novel is about 450,000 to 600,000 characters. A screenplay run turns an existing manuscript and a story bible into
a Fountain screenplay of up to 195 pages (ledger F8), so it needs the manuscript itself.

## Decision

- A `screenplay` run takes a **source folder**, not run inputs. Each `.md` or `.txt` file in the folder, sorted by name, is
  one source. A file over 2,000,000 bytes is refused rather than truncated, so the author sees a short source, not a
  clipped one.
- Each source becomes a write-once artifact `source/NNN.md` with a SHA-256 digest recorded alongside it, so a changed
  source is visible in the run's record. Hidden files and other file types are skipped.
- The file's text is untrusted: a file holding control characters (other than tab and line breaks) is refused.
- An empty folder is refused (`SOURCE_EMPTY`); a missing folder is refused (`SOURCE_FOLDER_MISSING`).
- The run inputs of ADR 0011 are unchanged for every other kind of book.

## Consequences

- The screenplay run's drafting can read each sequence's own source files, not the whole novel, so no call holds more
  than its sequence (see the screenplay plan, PR 4).
- The source folder is the author's; nothing from it is committed to this repository.
- Wiring this into `ei book create` (a `--source` flag) and a `source` pipeline stage follows in the next pull request.
