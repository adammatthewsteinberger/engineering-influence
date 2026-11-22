# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Outline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.chapter_outline import ChapterOutline


class OutlineInterface(ABC):
    """The chapters of a non-fiction book, in order, as the drafting stage will walk them."""

    __slots__ = ()

    @abstractmethod
    def count(self) -> int:
        """How many chapters there are."""

    @abstractmethod
    def chapter(self, number: int) -> ChapterOutline:
        """The chapter with this number, or a ValueError when there is none."""
