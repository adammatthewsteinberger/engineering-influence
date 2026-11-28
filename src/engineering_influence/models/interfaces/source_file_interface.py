# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SourceFile."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SourceFileInterface(ABC):
    """A file the author supplied as source material for a screenplay."""

    __slots__ = ()

    @abstractmethod
    def text(self) -> str:
        """The file's text, exactly as the author wrote it."""
