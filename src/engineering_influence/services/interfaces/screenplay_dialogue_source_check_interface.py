# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayDialogueSourceCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayDialogueSourceCheckInterface(ABC):
    """Checks that a drafted scene's dialogue does not copy the sources it was written from."""

    __slots__ = ()

    @abstractmethod
    def problems(self, scene: str, sources: str) -> tuple[str, ...]:
        """Every speech that repeats a run of source words, or nothing when no speech copies the sources."""
