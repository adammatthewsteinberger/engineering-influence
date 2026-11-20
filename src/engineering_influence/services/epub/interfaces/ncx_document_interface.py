# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for NcxDocument."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.book import Book
    from engineering_influence.services.epub.ncx_document import Entries


class NcxDocumentInterface(ABC):
    """Parts as navPoints containing their chapters."""

    __slots__ = ()

    @abstractmethod
    def render(self, entries: Entries, book: Book, uid: str) -> str:
        """Return the NCX XML."""
