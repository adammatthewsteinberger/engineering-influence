# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BibleCardParser."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.bible_card import BibleCard
    from engineering_influence.models.bible_file import BibleFile


class BibleCardParserInterface(ABC):
    """Reads one card's front matter and body, and a bible's schema."""

    __slots__ = ()

    @abstractmethod
    def card(self, file: BibleFile) -> BibleCard:
        """The card in the file. Raise an ApplicationError when its front matter is missing, unclosed or not TOML."""

    @abstractmethod
    def schema(self, text: str) -> dict[str, tuple[str, ...]]:
        """The required keys of each kind, from bible.toml's `[required]` table. Empty when the text is empty."""
