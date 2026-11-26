# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplaySectionCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplaySectionCheckInterface(ABC):
    """Checks one drafted scene before it is kept."""

    __slots__ = ()

    @abstractmethod
    def problems(self, section: str) -> tuple[str, ...]:
        """Every problem with the scene, or nothing when it is one scene that follows the format."""
