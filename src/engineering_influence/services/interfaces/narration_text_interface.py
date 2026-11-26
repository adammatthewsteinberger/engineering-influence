# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for NarrationText."""

from __future__ import annotations

from abc import ABC, abstractmethod


class NarrationTextInterface(ABC):
    """Turns a chapter of the manuscript into the plain segments a narrator reads."""

    __slots__ = ()

    @abstractmethod
    def segments(self, markdown: str) -> tuple[str, ...]:
        """The chapter as speakable segments, in order, none longer than a narrator can take at once."""
