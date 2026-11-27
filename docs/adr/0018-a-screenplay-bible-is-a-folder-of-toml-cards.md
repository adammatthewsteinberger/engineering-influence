# ADR 0018: A screenplay's bible is a folder of TOML cards, checked as a whole

Status: accepted

## Context

A screenplay is written from a source folder (ADR 0017) and a bible: the characters, places and things the film must keep
consistent from scene to scene. The author already keeps the bible as cards, one file each, in their own folder. The
pipeline needs to read those cards without copying them into this repository, and to refuse a bible that would make the
drafting inconsistent (two cards with one id, a link to a card that does not exist, a real person with no clearance).

## Decision

- A bible is a folder. Each subfolder is a **kind** (`character`, `place`, ...), and each `.md` file in it is one card whose
  **id** is the file name without the extension. A kind is a lowercase identifier (`[a-z][a-z0-9_]*`); an id is a lowercase
  identifier that may contain `-` (`[a-z0-9][a-z0-9_-]*`). Hidden files and folders are skipped.
- A card begins with TOML front matter between two `+++` lines, and the Markdown body follows the second line.
- `bible.toml` at the root is optional. Its `[required]` table names the front-matter keys each kind must set:
  `character = ["name", "role"]`. A kind with no entry has no required keys.
- An id is unique within its kind (`BIBLE_DUPLICATE_ID`). A body may link to another card as `[[kind: id]]`, and every link
  must name an existing card (`BIBLE_LINK_UNKNOWN`). Links are read from the body only.
- A card with `real = true` is a real person (or any real thing the author must clear). Such a card must name its
  `clearance`, which says who agreed or where the fact is public record, and must not carry a `likeness` or `voice` key:
  the pipeline never prompts a likeness or a voice (`BIBLE_REAL_PERSON`).
- The bible is read-only and is the author's. Nothing from it is committed to this repository.

## Consequences

- The loader checks the whole bible before a run uses it, so drafting never meets a dangling link.
- The card format is the author's to extend: a new key in a card needs no code change, and a new required key is one line
  in `bible.toml`.
- Wiring the bible into a run (a `--bible` flag beside `--source`) and handing it to drafting is the next pull request.
