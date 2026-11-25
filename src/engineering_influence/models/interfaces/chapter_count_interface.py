# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ChapterCount."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ChapterCountInterface(ABC):
    """One rule for how many chapters a book of a target length should have, and whether an outline is near it."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def for_target(cls, target_words: int | None) -> int | None:
        """The number of chapters for the target, or None when the brief gives no target."""

    @classmethod
    @abstractmethod
    def mismatch(cls, target_words: int | None, chapters: int) -> str | None:
        """Why an outline of ``chapters`` chapters is the wrong size for the target, or None when it is right enough."""
