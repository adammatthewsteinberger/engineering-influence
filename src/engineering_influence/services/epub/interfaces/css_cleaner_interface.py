# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CssCleaner."""

from abc import ABC, abstractmethod


class CssCleanerInterface(ABC):
    """Nothing in an ebook needs to be hidden."""

    __slots__ = ()

    @abstractmethod
    def strip_hidden_rules(self, css: str) -> str:
        """Drop every rule that hides an element."""
