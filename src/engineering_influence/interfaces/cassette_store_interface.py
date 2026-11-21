# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: where recorded model exchanges are kept."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.cassette import Cassette


class CassetteStoreInterface(ABC):
    """Reads and writes cassettes by name."""

    __slots__ = ()

    @abstractmethod
    def load(self, name: str) -> Cassette:
        """The named cassette, or an ApplicationError (CASSETTE_INVALID) when it is not usable."""

    @abstractmethod
    def save(self, cassette: Cassette) -> None:
        """Keep the cassette, or raise an ApplicationError (CASSETTE_INVALID) rather than keep a secret."""
