# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ReferenceParser."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.verse_ref import VerseRef


class ReferenceParserInterface(ABC):
    """Finds the Bible references written in a text."""

    __slots__ = ()

    @abstractmethod
    def find(self, text: str) -> tuple[tuple[int, int, tuple[VerseRef, ...]], ...]:
        """Each reference in the text, as (start, end, verses), in the order they appear."""
