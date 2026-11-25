# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: a recording of the exchanges a model adapter has with its provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.cassette import Cassette


class CassetteRecorderInterface(ABC):
    """Keeps what passed through it, with secrets masked, as a cassette."""

    __slots__ = ()

    @abstractmethod
    def finish(self, name: str, provider: str, note: str = "") -> Cassette:
        """Save what was recorded as the named cassette and return it."""
