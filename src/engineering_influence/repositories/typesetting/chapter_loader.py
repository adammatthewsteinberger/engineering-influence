# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads one manuscript file into a Chapter."""

import re
from pathlib import Path

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.models.publishing.path_relativizer import PathRelativizer
from engineering_influence.models.typesetting.chapter import Chapter
from engineering_influence.models.typesetting.running_head import RunningHead
from engineering_influence.models.typesetting.text_policy import TextPolicy
from engineering_influence.repositories.typesetting.interfaces.chapter_loader_interface import (
    ChapterLoaderInterface,
)


class ChapterLoader(ChapterLoaderInterface):
    """Parses the title, epigraph, and body; refuses unfinished markers when strict."""

    UNFINISHED = r"\[(TESTIMONY|PLACEHOLDER|TODO|TBD|VERIFY|LIKELY|INSERT)[^\]]*\]"
    FORBIDDEN_MARKERS = re.compile(UNFINISHED + r"|\u2014|\u2013")
    # A novel may use em dashes, so only unfinished markers and en dashes are refused.
    FORBIDDEN_IN_FICTION = re.compile(UNFINISHED + r"|\u2013")
    TITLE_PREFIX = re.compile(r"^(Chapter\s+(\d+|[A-Z][a-z]+(-[a-z]+)?)\s*[:.]\s*)", re.IGNORECASE)

    def __init__(
        self,
        relativizer: PathRelativizer,
        strict: bool = True,
        policy: TextPolicy | None = None,
    ) -> None:
        """Remember the path relativizer, whether unfinished markers are refused, and the text policy."""
        self._relativizer = relativizer
        self._strict = strict
        fiction = policy is not None and policy.allows_em_dash
        self._forbidden = self.FORBIDDEN_IN_FICTION if fiction else self.FORBIDDEN_MARKERS

    def load(self, path: Path, kind: str, style: str, short: str | None) -> Chapter:
        """Read the file at path."""
        text = path.read_text(encoding="utf-8")
        bad = self._forbidden.search(text)
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
