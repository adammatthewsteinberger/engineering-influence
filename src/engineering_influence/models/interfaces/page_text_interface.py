# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PageText."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PageTextInterface(ABC):
    """The readable text of a page, and its title."""

    __slots__ = ()

    @abstractmethod
    def is_empty(self) -> bool:
        """True when there is no text a reader would see."""
