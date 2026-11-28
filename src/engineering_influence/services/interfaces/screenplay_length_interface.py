# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayLength."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayLengthInterface(ABC):
    """Decides whether a screenplay's length is within the film's running time."""

    __slots__ = ()

    @abstractmethod
    def problems(self, pages: int) -> tuple[str, ...]:
        """Why the length is not acceptable, or nothing when it is."""
