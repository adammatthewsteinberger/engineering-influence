# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PrintDocument."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.book import Book


class PrintDocumentInterface(ABC):
    """Half title, title page, copyright, dedication, contents, chapters, and author note."""

    __slots__ = ()

    @abstractmethod
    def render(self, book: Book, hardcover: bool = False) -> str:
        """Return the complete .tex source."""
