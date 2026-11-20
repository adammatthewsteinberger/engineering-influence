# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for XhtmlCleaner."""

from abc import ABC, abstractmethod


class XhtmlCleanerInterface(ABC):
    """Drops empty stubs, hoists heading ids, and adds xml:lang."""

    __slots__ = ()

    @abstractmethod
    def clean(self, xhtml: str) -> str:
        """Return cleaned XHTML."""
