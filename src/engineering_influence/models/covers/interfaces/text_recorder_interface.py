# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TextRecorder."""

from abc import ABC, abstractmethod


class TextRecorderInterface(ABC):
    """Per-render state that replaces a module-level list, so renders never share it."""

    __slots__ = ()

    @abstractmethod
    def record(self, size: int) -> None:
        """Note one run of text at an em size in pixels."""

    @abstractmethod
    def smallest(self) -> int | None:
        """The smallest size drawn, or None when nothing was drawn."""
