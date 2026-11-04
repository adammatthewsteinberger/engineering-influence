"""Printed-text rules for the ebook: no dashes, markers, drafts, or straight quotes."""

import re

from engineering_influence.publishing.epub.epub_contents import EpubContents
from engineering_influence.publishing.typesetting.book import Book


class TextRulesCheck:
    """The same editorial gates as the print interior."""

    MARKERS = ("[CALLOUT", "[/CALLOUT", "[ILLUSTRATION", "[TESTIMONY", "[PLACEHOLDER")

    def run(self, contents: EpubContents, book: Book, full: str) -> list[str]:
        """Return a problem for each rule the text breaks."""
        problems: list[str] = []
        for label, char in (("em dash", "—"), ("en dash", "–")):
            if char in full:
                problems.append(f"the ebook contains an {label}")
        for marker in self.MARKERS:
            if marker in full:
                problems.append(f"marker {marker!r} appears in the ebook")
        if re.search(r"\bDraft\b", full):
            problems.append("the word 'Draft' appears in the ebook")
        pages = "".join(v for k, v in contents.docs.items() if k.endswith(".xhtml"))
        if '"' in re.sub(r"<[^>]*>", "", pages):
            problems.append("a straight double quote appears in the text")
        if book.meta["edition"] not in full:
            problems.append(f"edition line {book.meta['edition']!r} not found")
        return problems
