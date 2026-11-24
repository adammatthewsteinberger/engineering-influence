# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScoreParser."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScoreParserInterface(ABC):
    """Reads a judge's answer as scores, and refuses one that is not a complete, well-formed set."""

    __slots__ = ()

    @abstractmethod
    def parse(self, text: str, dimensions: tuple[str, ...]) -> tuple[tuple[str, int, str], ...]:
        """The (dimension, score, reason) of each dimension, in the order given; an ApplicationError if the answer is unusable."""
