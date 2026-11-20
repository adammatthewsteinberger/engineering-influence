# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TextRulesCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents
    from engineering_influence.models.typesetting.book import Book


class TextRulesCheckInterface(ABC):
    """The same editorial gates as the print interior."""

    __slots__ = ()

    @abstractmethod
    def run(self, contents: EpubContents, book: Book, full: str) -> list[str]:
        """Return a problem for each rule the text breaks."""
