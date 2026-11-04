# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""API key verifier port."""

from abc import ABC, abstractmethod


class ApiKeyVerifierPort(ABC):
    """Decide whether a presented API key is valid."""

    @abstractmethod
    def verify(self, presented: str | None) -> bool:
        """Return True only for a configured key; missing input is never valid."""
