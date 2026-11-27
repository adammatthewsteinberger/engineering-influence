# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BibleFile."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BibleFileInterface(ABC):
    """One card's file as the author keeps it: its kind, its id and its text."""

    __slots__ = ()

    @abstractmethod
    def path(self) -> str:
        """The card's place in the bible, `kind/id.md`, for an error message."""
