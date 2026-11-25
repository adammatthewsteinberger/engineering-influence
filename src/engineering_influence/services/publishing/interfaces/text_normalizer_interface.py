# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TextNormalizer."""

from abc import ABC, abstractmethod


class TextNormalizerInterface(ABC):
    """Lowercases, folds quotes, and strips punctuation and whitespace."""

    __slots__ = ()

    @abstractmethod
    def normalize(self, text: str) -> str:
        """Return a comparison key for the text."""
