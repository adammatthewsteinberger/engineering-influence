# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ChapterOutline."""

from abc import ABC, abstractmethod


class ChapterOutlineInterface(ABC):
    """What the outline says about one chapter: its title, purpose, beats and the claims it will need sources for."""

    __slots__ = ()

    @abstractmethod
    def heading(self) -> str:
        """The chapter as people name it: ``Chapter 3: The Hive``."""
