# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TexText."""

from abc import ABC, abstractmethod


class TexTextInterface(ABC):
    """Escapes plain metadata, keeping line breaks."""

    __slots__ = ()

    @abstractmethod
    def text(self, s: str) -> str:
        """Render one metadata string."""

    @abstractmethod
    def paragraphs(self, s: str) -> str:
        """Render blank-line separated paragraphs."""
