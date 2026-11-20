# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for JournalKey."""

from abc import ABC, abstractmethod


class JournalKeyInterface(ABC):
    """What identifies one model request, so a repeat of it can be replayed."""

    __slots__ = ()

    @abstractmethod
    def digest(self) -> str:
        """A stable SHA-256 of the four parts; the same request always gives the same digest."""
