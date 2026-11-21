# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Cassette."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.cassette_interaction import CassetteInteraction


class CassetteInterface(ABC):
    """The exchanges one test replays, in order."""

    __slots__ = ()

    @abstractmethod
    def interaction_at(self, position: int) -> CassetteInteraction | None:
        """The exchange at this position (counting from 0), or None once they are all used."""
