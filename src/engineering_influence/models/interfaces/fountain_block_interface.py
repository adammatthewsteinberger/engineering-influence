# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FountainBlock."""

from __future__ import annotations

from abc import ABC, abstractmethod


class FountainBlockInterface(ABC):
    """One element of a Fountain screenplay, as it reads in the source."""

    __slots__ = ()

    @abstractmethod
    def text(self) -> str:
        """The element's lines joined with newlines."""
