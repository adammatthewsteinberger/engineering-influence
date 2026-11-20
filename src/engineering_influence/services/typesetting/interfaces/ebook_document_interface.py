# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EbookDocument."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.book import Book


class EbookDocumentInterface(ABC):
    """The same chapters as the print interior, set with the fine-ebook class."""

    __slots__ = ()

    @abstractmethod
    def render(self, book: Book) -> str:
        """Return the complete .tex source."""
