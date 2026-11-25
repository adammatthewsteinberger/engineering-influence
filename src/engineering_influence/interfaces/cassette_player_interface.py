# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: a replay of a cassette that can say whether the code used all of it."""

from __future__ import annotations

from abc import ABC, abstractmethod


class CassettePlayerInterface(ABC):
    """Answers requests from a cassette and checks that none was left unused."""

    __slots__ = ()

    @abstractmethod
    def remaining(self) -> int:
        """How many recorded exchanges have not been replayed yet."""

    @abstractmethod
    def finish(self) -> None:
        """Raise an ApplicationError (CASSETTE_MISMATCH) if any recorded exchange was never replayed."""
