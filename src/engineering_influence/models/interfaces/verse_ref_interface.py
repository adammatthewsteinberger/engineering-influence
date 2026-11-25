# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for VerseRef."""

from __future__ import annotations

from abc import ABC, abstractmethod


class VerseRefInterface(ABC):
    """One verse of the Bible, by its book code, chapter and verse."""

    __slots__ = ()

    @abstractmethod
    def label(self) -> str:
        """The verse as a reader writes it, such as ``JHN 3:16``."""
