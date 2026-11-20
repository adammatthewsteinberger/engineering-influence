# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for HeadingIds."""

from abc import ABC, abstractmethod


class HeadingIdsInterface(ABC):
    """Finds the anchors a contents link may target."""

    __slots__ = ()

    @abstractmethod
    def all(self, xhtml: str) -> list[str]:
        """Every id on or inside a heading element, in document order."""

    @abstractmethod
    def own(self, xhtml: str) -> list[str]:
        """The id attribute of each heading element itself."""
