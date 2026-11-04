# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contents labels, in reading order, from the book model."""

import html
import re

from engineering_influence.publishing.typesetting.book import Book
from engineering_influence.publishing.typesetting.markdown_parser import MarkdownParser


class TocLabels:
    """Parts at depth 0 with their chapters at depth 1; front and back matter at depth 0."""

    NUMBER_WORDS = (
        "Zero",
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Six",
        "Seven",
        "Eight",
        "Nine",
        "Ten",
        "Eleven",
        "Twelve",
    )

    def __init__(self) -> None:
        self._parser = MarkdownParser()

    def for_book(self, book: Book) -> list[tuple[str, int]]:
        """Return (label, depth) for every contents entry."""
        out = [(self._smart(chapter.title), 0) for chapter in book.front]
        number = 0
        for part_number, (part_title, chapters) in enumerate(book.parts, 1):
            out.append((f"Part {self.NUMBER_WORDS[part_number]}: {self._smart(part_title)}", 0))
            for chapter in chapters:
                number += 1
                out.append((f"{number}. {self._smart(chapter.title)}", 1))
        out += [
            (
                f"{chapter.number} {self._smart(chapter.title)}"
                if chapter.number
                else self._smart(chapter.title),
                0,
            )
            for chapter in book.back
        ]
        out.append(("About the Author", 0))
        return out

    def _smart(self, s: str) -> str:
        """Plain text with the same curly quotes and apostrophes the pages use."""
        return html.unescape(re.sub(r"<[^>]+>", "", self._parser.render_inline(s)))
