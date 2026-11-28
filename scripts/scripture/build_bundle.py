# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Turns the public-domain USFM archives from eBible.org into the verse files the product bundles.

Usage: python scripts/scripture/build_bundle.py ZIP_DIR OUT_DIR

ZIP_DIR holds ``web.zip``, ``kjv.zip``, ``asv.zip``, ``ylt.zip``, ``dra.zip`` and ``bsb.zip`` (the ``*_usfm.zip``
files from eBible.org, renamed). Each becomes ``OUT_DIR/<translation>.txt.gz``: one line per verse, ``BOOK C:V<TAB>text``,
in canonical order, with the notes, cross-references, headings and introductions left out. The output is deterministic
(gzip mtime fixed), so rebuilding from the same archives gives the same bytes, and ``SOURCES.md`` records each archive's
SHA-256.
"""

import gzip
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path

TRANSLATIONS = ("web", "kjv", "asv", "ylt", "dra", "bsb")
NOTE = re.compile(r"\\f\s.*?\\f\*|\\x\s.*?\\x\*", re.DOTALL)
WORD = re.compile(r"\\w\s+(.*?)\\w\*", re.DOTALL)
VERSE = re.compile(r"^\\v\s+(\d+)(?:\s*[-\u2013]\s*(\d+))?\s*(.*)$")
CHAPTER = re.compile(r"^\\c\s+(\d+)")
BOOK = re.compile(r"^\\id\s+([A-Z0-9]{3})")
# Lines that are headings, titles, notes or introductions: never verse text.
SKIPPED = (
    "\\s",
    "\\r",
    "\\d",
    "\\sp",
    "\\mt",
    "\\mr",
    "\\ms",
    "\\h",
    "\\toc",
    "\\ip",
    "\\im",
    "\\io",
    "\\iot",
    "\\ie",
    "\\cl",
    "\\cp",
    "\\ca",
    "\\cd",
    "\\rem",
)


def clean(text: str) -> str:
    """The verse with its notes removed, words unwrapped, and every remaining marker taken out."""
    text = NOTE.sub(" ", text)
    text = WORD.sub(lambda match: match.group(1).split("|")[0], text)
    text = re.sub(r"\\\+?[A-Za-z0-9]+\*?", " ", text)
    text = re.sub(r"\|[^\s]*", "", text)
    text = text.replace("\u00b6", " ")
    text = re.sub(r"\s+([,.;:!?\u201d\u2019)\]])", r"\1", text)
    return " ".join(text.split())


def verses(usfm: str) -> list[tuple[str, int, int, str]]:
    """Every verse in the file, as (book, chapter, verse, text), in the order the file gives them."""
    found: list[tuple[str, int, int, str]] = []
    book = ""
    chapter = 0
    current: list[tuple[int, list[str], int | None]] = []

    def flush() -> None:
        for number, parts, last in current:
            text = clean(" ".join(parts))
            found.append((book, chapter, number, text))
            if last is not None:
                found.append((book, chapter, last, text))
        current.clear()

    for raw in usfm.splitlines():
        line = raw.strip()
        if not line:
            continue
        if match := BOOK.match(line):
            flush()
            book = match.group(1)
            continue
        if match := CHAPTER.match(line):
            flush()
            chapter = int(match.group(1))
            continue
        if match := VERSE.match(line):
            flush()
            number = int(match.group(1))
            last = int(match.group(2)) if match.group(2) else None
            current.append((number, [match.group(3)], last))
            continue
        if line.startswith(SKIPPED) or line.startswith("\\i") or not line.startswith("\\"):
            if line.startswith("\\") or not current:
                continue
            current[-1][1].append(line)
            continue
        if current:
            current[-1][1].append(line)
    flush()
    return found


def build(zip_dir: Path, out_dir: Path) -> dict[str, str]:
    """Write one zip bundle per translation into the output folder, with a digest of each."""
    out_dir.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}
    for name in TRANSLATIONS:
        archive = zip_dir / f"{name}.zip"
        data = archive.read_bytes()
        digests[name] = hashlib.sha256(data).hexdigest()
        lines = []
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            for member in sorted(bundle.namelist()):
                if not member.lower().endswith(".usfm"):
                    continue
                for book, chapter, number, text in verses(bundle.read(member).decode("utf-8-sig")):
                    if book and chapter and text:
                        lines.append(f"{book} {chapter}:{number}\t{text}")
        target = out_dir / f"{name}.txt.gz"
        with (
            open(target, "wb") as raw,
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as packed,
        ):
            packed.write(("\n".join(lines) + "\n").encode("utf-8"))
        print(f"{name}: {len(lines)} verses -> {target.name}")
    return digests


def main(argv: list[str]) -> int:
    """Build the bundles from the zip folder and the output folder given on the command line."""
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    digests = build(Path(argv[1]), Path(argv[2]))
    lines = ["# Sources", ""] + [
        f"- {name}.zip sha256 {digest}" for name, digest in digests.items()
    ]
    (Path(argv[2]) / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
