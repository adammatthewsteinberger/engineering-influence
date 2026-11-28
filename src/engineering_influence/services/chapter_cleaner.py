# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Turns a drafted chapter into Markdown that passes the typesetter's text rules."""

import re
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.services.interfaces.chapter_cleaner_interface import (
    ChapterCleanerInterface,
)
from engineering_influence.services.interfaces.dash_rewriter_interface import (
    DashRewriterInterface,
)


class ChapterCleaner(ChapterCleanerInterface):
    """What the drafting stage wrote, made into what ``BookLoader`` reads in strict mode.

    The typesetter refuses a non-fiction book that has an em dash or an en dash, an unfinished marker such
    as ``[TODO]``, or the word ``Draft``. A model's prose has dashes in it all the time, so those are
    **rewritten**: a dash between two digits becomes a hyphen (``1990-1995``), and any other dash becomes a
    comma, or nothing at the start or end of a line or before punctuation (see ``DashRewriter``). A marker, or the word ``Draft``, is **refused**, with the chapter
    and the line, because deleting one would hide that the chapter was not finished.

    The chapter's own title is the outline's, so a heading the model put at the top of its answer
    (``Chapter 2: The Site``, with or without ``#``) is dropped and ``# Title`` written in its place. Any
    other level-1 heading in the body is made a level-2 one, because a chapter has one title; text
    inside a fenced block is left as it is.
    """

    MARKERS: ClassVar[re.Pattern[str]] = re.compile(
        r"\[/?(?:TESTIMONY|PLACEHOLDER|TODO|TBD|VERIFY|LIKELY|INSERT|CALLOUT|ILLUSTRATION)"
    )
    DRAFT: ClassVar[re.Pattern[str]] = re.compile(r"\bDraft\b")
    HEADING: ClassVar[re.Pattern[str]] = re.compile(r"^\s*(?:#{1,6}\s+\S.*|Chapter\s+\d+\b.*)$")
    FENCE: ClassVar[re.Pattern[str]] = re.compile(r"^\s*(```|~~~)")

    def __init__(self, dashes: DashRewriterInterface) -> None:
        """Remember the dash rewriter used when cleaning the drafted chapters."""
        self._dashes = dashes

    def clean(self, number: int, title: str, text: str) -> str:
        """The chapter as ``# Title`` and a clean body."""
        self._refuse_unfinished(number, text)
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        first = next((index for index, line in enumerate(lines) if line.strip()), len(lines))
        if first < len(lines) and self.HEADING.match(lines[first]):
            lines = lines[first + 1 :]
        body = self._dashes.rewrite(self._demoted(lines)).strip("\n")
        if not body.strip():
            raise ApplicationError(
                code="MANUSCRIPT_TEXT_REFUSED",
                message=f"chapter {number} has no text after its heading",
                http_status=422,
            )
        return f"# {title}\n\n{body}\n"

    def _refuse_unfinished(self, number: int, text: str) -> None:
        for pattern, what in (
            (self.MARKERS, "an unfinished marker"),
            (self.DRAFT, "the word 'Draft'"),
        ):
            found = pattern.search(text)
            if found:
                line = text[: found.start()].count("\n") + 1
                raise ApplicationError(
                    code="MANUSCRIPT_TEXT_REFUSED",
                    message=f"chapter {number}, line {line}: {what} ({found.group(0)!r}); "
                    "the book cannot be typeset with it",
                    http_status=422,
                )

    def _demoted(self, lines: list[str]) -> str:
        fenced = False
        kept = []
        for line in lines:
            if self.FENCE.match(line):
                fenced = not fenced
            elif not fenced and line.startswith("# "):
                line = "#" + line
            kept.append(line)
        return "\n".join(kept)
