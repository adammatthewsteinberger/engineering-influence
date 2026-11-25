# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ManuscriptText."""

from abc import ABC, abstractmethod


class ManuscriptTextInterface(ABC):
    """Titles, bodies, and prose paragraphs of a Markdown source file."""

    __slots__ = ()

    @abstractmethod
    def normalise(self, text: str) -> str:
        """Lowercase and keep only letters and digits."""

    @abstractmethod
    def title_and_body(self, text: str) -> tuple[str, str] | None:
        """Split on the level-1 title; None when the first line is not one."""

    @abstractmethod
    def paragraphs(self, body: str) -> list[str]:
        """Prose paragraphs, skipping blocks made only of block quotes (epigraphs)."""
