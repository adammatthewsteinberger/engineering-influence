# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplaySceneCardsCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplaySceneCardsCheckInterface(ABC):
    """The mechanical checks on a screenplay's scene cards (prompt 08, step 8.2.2)."""

    __slots__ = ()

    @abstractmethod
    def problems(self, text: str) -> tuple[str, ...]:
        """Every way the scene cards break the format, or nothing when they pass."""
