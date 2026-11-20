# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TocLabels."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.book import Book


class TocLabelsInterface(ABC):
    """Parts at depth 0 with their chapters at depth 1; front and back matter at depth 0."""

    __slots__ = ()

    @abstractmethod
    def for_book(self, book: Book) -> list[tuple[str, int]]:
        """Return (label, depth) for every contents entry."""
