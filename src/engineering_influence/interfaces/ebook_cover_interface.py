# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for the ebook's cover image."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.book import Book


class EbookCoverInterface(ABC):
    """Provide the ebook's internal cover as JPEG bytes."""

    __slots__ = ()

    @abstractmethod
    def jpeg(self, book: Book) -> bytes:
        """The cover for the book; raise BookBuildError when it has not been built."""
