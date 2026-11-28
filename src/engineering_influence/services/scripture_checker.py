# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks the quotations of Scripture in a chapter against the verses they cite, in the bundled translations."""

import re
from difflib import SequenceMatcher
from typing import ClassVar

from engineering_influence.interfaces.scripture_index_interface import ScriptureIndexInterface
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.verse_ref import VerseRef
from engineering_influence.services.interfaces.reference_parser_interface import (
    ReferenceParserInterface,
)
from engineering_influence.services.interfaces.scripture_checker_interface import (
    ScriptureCheckerInterface,
)


class ScriptureChecker(ScriptureCheckerInterface):
    """A quotation (in curly or straight quotes, at least four words) that is followed by its citation is checked.

    The quotation is word for word in a bundled translation of the cited verses: that is correct, and nothing is
    reported. It is close (at least ``NEAR`` of its words are in the verses, in order) to a translation: reported as
    ``SCRIPTURE_NEAR``, because the author may have quoted from memory or from another edition. Otherwise it is
    ``SCRIPTURE_MISQUOTED``. When no bundled translation has the verses, the quotation cannot be checked and is
    reported as ``SCRIPTURE_UNCHECKED``. A citation must come within ``CITED_WITHIN`` characters of the closing quote.

    Every finding is non-blocking: a human reads the book, and a wrong quotation is for the author to fix, not a reason to
    stop the run. The comparison ignores case, punctuation and quotation marks, so typographic differences are not
    findings.
    """

    QUOTE: ClassVar[re.Pattern[str]] = re.compile(
        r"[\u201c\"]([^\u201c\u201d\"]{12,600}?)[\u201d\"]"
    )
    MIN_WORDS: ClassVar[int] = 4
    REACH: ClassVar[int] = 140
    CITED_WITHIN: ClassVar[int] = 40
    NEAR: ClassVar[float] = 0.9
    PLAIN: ClassVar[re.Pattern[str]] = re.compile(r"[^a-z0-9 ]+")

    def __init__(
        self, scripture: ScriptureIndexInterface, references: ReferenceParserInterface
    ) -> None:
        """Remember the scripture index and the reference parser the quotations are checked with."""
        self._scripture = scripture
        self._references = references

    def check(self, chapter: int, text: str) -> tuple[QualityIssue, ...]:
        """The findings for the chapter's quotations, in the order they appear."""
        found: list[QualityIssue] = []
        for quote in self.QUOTE.finditer(text):
            quoted = quote.group(1)
            if len(quoted.split()) < self.MIN_WORDS:
                continue
            cited = self._cited(text[quote.end() : quote.end() + self.REACH])
            if cited is None:
                continue
            issue = self._compare(chapter, quoted, cited)
            if issue is not None:
                found.append(issue)
        return tuple(found)

    def _cited(self, window: str) -> tuple[VerseRef, ...] | None:
        citations = self._references.find(window)
        if not citations or citations[0][0] > self.CITED_WITHIN:
            return None
        return citations[0][2]

    def _compare(
        self, chapter: int, quoted: str, cited: tuple[VerseRef, ...]
    ) -> QualityIssue | None:
        wanted = self._plain(quoted)
        label = self._label(cited)
        best_name, best = "", 0.0
        checked = False
        for translation in self._scripture.translations():
            verses = self._scripture.text(translation, cited)
            if verses is None:
                continue
            checked = True
            found = self._plain(verses)
            if wanted and wanted in found:
                return None
            share = self._share(wanted, found)
            if share > best:
                best_name, best = translation, share
        if not checked:
            return self._issue(
                "SCRIPTURE_UNCHECKED",
                f"chapter {chapter}: the quotation cited as {label} could not be checked: no bundled translation has those verses",
            )
        if best >= self.NEAR:
            return self._issue(
                "SCRIPTURE_NEAR",
                f"chapter {chapter}: the quotation cited as {label} is close to the {best_name} but not word for word",
            )
        return self._issue(
            "SCRIPTURE_MISQUOTED",
            f"chapter {chapter}: the quotation cited as {label} does not match those verses in any bundled translation",
        )

    @classmethod
    def _plain(cls, text: str) -> str:
        """Lower case, letters, digits and single spaces: the words, without punctuation or typography."""
        return " ".join(cls.PLAIN.sub(" ", text.lower()).split())

    @staticmethod
    def _share(wanted: str, found: str) -> float:
        """The share of the quoted words that appear, in order, in the verses."""
        quoted = wanted.split()
        if not quoted:
            return 0.0
        matcher = SequenceMatcher(None, quoted, found.split(), autojunk=False)
        matched = sum(block.size for block in matcher.get_matching_blocks())
        return matched / len(quoted)

    @staticmethod
    def _label(cited: tuple[VerseRef, ...]) -> str:
        if len(cited) == 1:
            return cited[0].label()
        return f"{cited[0].label()}-{cited[-1].verse}"

    @staticmethod
    def _issue(code: str, detail: str) -> QualityIssue:
        return QualityIssue("draft", code, detail, blocking=False)
