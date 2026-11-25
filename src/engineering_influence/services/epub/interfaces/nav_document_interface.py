# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for NavDocument."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.book import Book
    from engineering_influence.services.epub.nav_document import Entries


class NavDocumentInterface(ABC):
    """The toc nav (nested like the NCX) and the landmarks."""

    __slots__ = ()

    @abstractmethod
    def toc_list(self, entries: Entries) -> str:
        """The contents as a nested list: parts with their chapters inside, other matter flat."""

    @abstractmethod
    def render(self, entries: Entries, book: Book, toc_page: str, start_href: str) -> str:
        """Landmarks point Kindle's "Contents" at the HTML page and "Go to Beginning" at the."""
