# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Printed-text rules for the ebook: no dashes, markers, drafts, or straight quotes."""

import re

from engineering_influence.models.epub.epub_contents import EpubContents
from engineering_influence.models.typesetting.book import Book
from engineering_influence.models.typesetting.text_policy import TextPolicy
from engineering_influence.services.epub.interfaces.text_rules_check_interface import (
    TextRulesCheckInterface,
)


class TextRulesCheck(TextRulesCheckInterface):
    """The same editorial gates as the print interior, under the same text policy."""

    DIALOGUE = re.compile("\u201c[^\u201d]{0,500}\u201d")
    MARKERS = ("[CALLOUT", "[/CALLOUT", "[ILLUSTRATION", "[TESTIMONY", "[PLACEHOLDER")

    def run(self, contents: EpubContents, book: Book, full: str, policy: TextPolicy) -> list[str]:
        """Return a problem for each rule the text breaks."""
        problems: list[str] = []
        dashes = (
            [("en dash", "–")] if policy.allows_em_dash else [("em dash", "—"), ("en dash", "–")]
        )
        for label, char in dashes:
            if char in full:
                problems.append(f"the ebook contains an {label}")
        for marker in self.MARKERS:
            if marker in full:
                problems.append(f"marker {marker!r} appears in the ebook")
        prose = self.DIALOGUE.sub(" ", full) if policy.allows_draft_in_dialogue else full
        if re.search(r"\bDraft\b", prose):
            problems.append("the word 'Draft' appears in the ebook")
        pages = "".join(v for k, v in contents.docs.items() if k.endswith(".xhtml"))
        if '"' in re.sub(r"<[^>]*>", "", pages):
            problems.append("a straight double quote appears in the text")
        if book.meta["edition"] not in full:
            problems.append(f"edition line {book.meta['edition']!r} not found")
        return problems
