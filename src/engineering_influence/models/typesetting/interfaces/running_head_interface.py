# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RunningHead."""

from abc import ABC, abstractmethod


class RunningHeadInterface(ABC):
    """Uses the main clause of a long title."""

    __slots__ = ()

    @abstractmethod
    def make(self, title: str, limit: int = 42) -> str:
        """Return the title, or its main clause when the title is longer than the limit."""
