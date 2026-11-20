# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for OpeningFormatter."""

from abc import ABC, abstractmethod


class OpeningFormatterInterface(ABC):
    """Every reader-facing chapter opening receives the large initial."""

    __slots__ = ()

    @abstractmethod
    def format(self, latex: str) -> str:
        """Set the first word of a chapter as a drop cap plus small caps."""
