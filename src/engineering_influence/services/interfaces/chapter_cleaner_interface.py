# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ChapterCleaner."""

from abc import ABC, abstractmethod


class ChapterCleanerInterface(ABC):
    """Turns a drafted chapter into the Markdown the typesetter reads, or refuses it."""

    __slots__ = ()

    @abstractmethod
    def clean(self, number: int, title: str, text: str) -> str:
        """The chapter as ``# Title`` and a clean body, or an ApplicationError (MANUSCRIPT_TEXT_REFUSED)."""
