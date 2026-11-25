# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EpubIdentifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.book import Book


class EpubIdentifierInterface(ABC):
    """An ISBN-based identifier when the book has one, otherwise a stable UUID."""

    __slots__ = ()

    @abstractmethod
    def of(self, book: Book) -> tuple[str, str]:
        """Return (identifier, kind) where kind is "ISBN" or "UUID"."""

    @abstractmethod
    def meta_tex(self, book: Book) -> str:
        """Definitions read by fine-ebook.cfg. Only plain ASCII-safe values go here."""
