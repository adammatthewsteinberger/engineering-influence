# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Secret provider port."""

from abc import ABC, abstractmethod


class SecretProviderPort(ABC):
    """Read secrets and refuse to continue when one is missing."""

    @abstractmethod
    def require(self, name: str) -> str:
        """Return the secret or raise an ApplicationError; never return a default."""
