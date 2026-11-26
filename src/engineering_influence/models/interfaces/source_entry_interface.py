# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SourceEntry."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SourceEntryInterface(ABC):
    """A source file as the run stores it: its artifact name, its text, and the digest that pins it."""

    __slots__ = ()

    @abstractmethod
    def artifact(self) -> str:
        """The artifact name the run stores the text under."""
