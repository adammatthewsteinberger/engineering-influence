# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads one manuscript file into a Chapter."""

import re
from pathlib import Path

from engineering_influence.publishing.path_relativizer import PathRelativizer
from engineering_influence.publishing.typesetting.chapter import Chapter
from engineering_influence.publishing.typesetting.manuscript_error import ManuscriptError
from engineering_influence.publishing.typesetting.running_head import RunningHead


class ChapterLoader:
    """Parses the title, epigraph, and body; refuses unfinished markers when strict."""

    FORBIDDEN_MARKERS = re.compile(
        r"\[(TESTIMONY|PLACEHOLDER|TODO|TBD|VERIFY|LIKELY|INSERT)[^\]]*\]|\u2014|\u2013"
    )
    TITLE_PREFIX = re.compile(r"^(Chapter\s+(\d+|[A-Z][a-z]+(-[a-z]+)?)\s*[:.]\s*)", re.IGNORECASE)

    def __init__(self, relativizer: PathRelativizer, strict: bool = True) -> None:
        self._relativizer = relativizer
        self._strict = strict

    def load(self, path: Path, kind: str, style: str, short: str | None) -> Chapter:
        """Read the file at path."""
        text = path.read_text(encoding="utf-8")
        bad = self.FORBIDDEN_MARKERS.search(text)
        if bad and self._strict:
            line = text[: bad.start()].count("\n") + 1
            raise ManuscriptError(
                f"{self._relativizer.relative(path)}:{line}: "
                f"unfinished marker or dash {bad.group(0)!r}"
            )
        match = re.match(r"\s*#\s+(.+?)\s*\n", text)
        if not match:
            raise ManuscriptError(f"{path}: the first line must be a level-1 title")
        title = self.TITLE_PREFIX.sub("", match.group(1)).strip()
        body = text[match.end() :].strip("\n")
        epigraph = None
        quote = re.match(r"((?:>.*\n?)+)", body)
        if quote and kind == "chapter":
            lines = [re.sub(r"^>\s?", "", line) for line in quote.group(1).rstrip("\n").split("\n")]
            paragraphs = "\n".join(lines).strip().split("\n\n")
            if len(paragraphs) == 2 and len(paragraphs[1]) < 60:
                epigraph = (paragraphs[0].strip(), paragraphs[1].strip())
                body = body[quote.end() :].lstrip("\n")
        return Chapter(
            path=path,
            kind=kind,
            style=style,
            title=title,
            short=short or RunningHead().make(title),
            body=body,
            epigraph=epigraph,
        )
