# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SearchHit."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SearchHitInterface(ABC):
    """A link a search returned, and its title."""

    __slots__ = ()

    @abstractmethod
    def host(self) -> str:
        """The host the link points at, in lower case."""
