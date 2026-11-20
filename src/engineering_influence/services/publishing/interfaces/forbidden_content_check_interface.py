# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ForbiddenContentCheck."""

from abc import ABC, abstractmethod


class ForbiddenContentCheckInterface(ABC):
    """Dashes, placeholder markers, the word Draft, and the Edition line."""

    __slots__ = ()

    @abstractmethod
    def run(self, texts: list[str], edition: str) -> list[str]:
        """Return a problem for each forbidden item found in the page texts."""
