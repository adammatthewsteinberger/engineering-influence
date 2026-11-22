# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the outline stage's markdown into chapters, strictly."""

import re
import unicodedata
from typing import Any, ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.chapter_outline import ChapterOutline
from engineering_influence.models.outline import Outline
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)


class OutlineParser(OutlineParserInterface):
    """The contract between the outline stage and the stage that drafts from it.

    The outline stage is told to write, for each chapter in order, ``## Chapter N: Title``, then
    ``Purpose:`` (one sentence), ``Beats:`` and ``Claims to source:`` (bullet lists) and ``Leads to:``
    (one line).

    This reads that, and nothing else counts as a chapter. Text before the first chapter heading is
    ignored (a model's preamble). A label may be bold, a bullet may be ``-``, ``*``, a bullet dot or a
    number, and a line that wraps onto the next keeps its words, but only when no blank line comes between:
    a paragraph after a blank line (a closing note about front and back matter) belongs to no chapter and is
    left out rather than glued onto a beat. A chapter with no purpose or no beats, chapters that are not
    numbered 1, 2, 3 in order, or no chapters at all, is refused with a message that names the chapter and
    what is missing, so the person (or the stage that wrote it) can see why.

    What the model wrote is untrusted, so characters that render as nothing or act as controls are removed
    and every text is collapsed to one line. The result is data; it is never run.
    """

    HEADING: ClassVar[re.Pattern[str]] = re.compile(
        r"#{1,4}\s*(?:\*\*)?\s*Chapter\s+(\d+)\s*[:.–—-]\s*(.+?)\s*(?:\*\*)?",
        re.IGNORECASE,
    )
    LABEL: ClassVar[re.Pattern[str]] = re.compile(
        r"(?:\*\*)?\s*(Purpose|Beats|Claims to source|Leads to)\s*(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.*)",
        re.IGNORECASE,
    )
    BULLET: ClassVar[re.Pattern[str]] = re.compile(r"(?:[-*•]|\d{1,2}[.)])\s+(.+)")
    LISTS: ClassVar[dict[str, str]] = {"beats": "beats", "claims to source": "claims"}
    LINES: ClassVar[dict[str, str]] = {"purpose": "purpose", "leads to": "leads"}
    HIDDEN: ClassVar[frozenset[str]] = frozenset({"Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"})
    BLANKS: ClassVar[str] = "\t" + chr(0xA0)  # a tab and a non-breaking space read as a space

    def parse(self, text: str) -> Outline:
        """The outline, or an ApplicationError (OUTLINE_INVALID) saying what is wrong with the text."""
        drafts: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        section = ""
        after_blank = False
        for raw in text.splitlines():
            line = self._clean(raw)
            if not line:
                after_blank = True
                continue
            heading = self.HEADING.fullmatch(line)
            if heading:
                current = {
                    "number": int(heading.group(1)),
                    "title": heading.group(2),
                    "purpose": "",
                    "leads": "",
                    "beats": [],
                    "claims": [],
                }
                drafts.append(current)
                section, after_blank = "", False
                continue
            if current is not None:
                section = self._read(current, section, line, after_blank)
            after_blank = False
        return self._outline(drafts)

    def _read(self, current: dict[str, Any], section: str, line: str, after_blank: bool) -> str:
        label = self.LABEL.fullmatch(line)
        if label:
            name = label.group(1).lower()
            self._begin(current, name, label.group(2))
            return name
        bullet = self.BULLET.fullmatch(line)
        if bullet and section in self.LISTS:
            current[self.LISTS[section]].append(bullet.group(1))
        elif not after_blank:
            self._continue(current, section, line)
        return section

    def _begin(self, current: dict[str, Any], name: str, rest: str) -> None:
        if name in self.LINES:
            current[self.LINES[name]] = rest
        elif rest:
            bullet = self.BULLET.fullmatch(rest)
            current[self.LISTS[name]].append(bullet.group(1) if bullet else rest)

    def _continue(self, current: dict[str, Any], section: str, line: str) -> None:
        if section in self.LINES:
            key = self.LINES[section]
            current[key] = f"{current[key]} {line}".strip()
        elif section in self.LISTS and current[self.LISTS[section]]:
            items = current[self.LISTS[section]]
            items[-1] = f"{items[-1]} {line}"

    def _outline(self, drafts: list[dict[str, Any]]) -> Outline:
        if not drafts:
            raise self._invalid(
                "it has no chapters; each chapter starts with a heading like '## Chapter 1: Title'"
            )
        chapters = []
        for draft in drafts:
            try:
                chapters.append(
                    ChapterOutline(
                        number=draft["number"],
                        title=draft["title"],
                        purpose=draft["purpose"],
                        beats=tuple(draft["beats"]),
                        claims=tuple(draft["claims"]),
                        leads_to=draft["leads"],
                    )
                )
            except ValueError as error:
                raise self._invalid(f"chapter {draft['number']}: {error}") from error
        try:
            return Outline(tuple(chapters))
        except ValueError as error:
            raise self._invalid(str(error)) from error

    def _clean(self, raw: str) -> str:
        kept = "".join(
            " " if char in self.BLANKS else char
            for char in raw
            if char in self.BLANKS or unicodedata.category(char) not in self.HIDDEN
        )
        return " ".join(kept.split())

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(
            code="OUTLINE_INVALID", message=f"the outline cannot be read: {why}", http_status=422
        )
