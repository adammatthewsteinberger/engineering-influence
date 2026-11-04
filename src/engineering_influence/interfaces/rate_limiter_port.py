# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Rate limiter port."""

from abc import ABC, abstractmethod


class RateLimiterPort(ABC):
    """Admit or refuse one unit of work for a caller key."""

    @abstractmethod
    def allow(self, key: str) -> bool:
        """Consume one unit for the key and return whether it was admitted."""
