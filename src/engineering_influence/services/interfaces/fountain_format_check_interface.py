# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FountainFormatCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod


class FountainFormatCheckInterface(ABC):
    """Prompt 09's mechanical format test, and the notes a person should read."""

    __slots__ = ()

    @abstractmethod
    def problems(self, text: str) -> tuple[str, ...]:
        """Every format rule the script breaks, or nothing when it passes."""

    @abstractmethod
    def notes(self, text: str) -> tuple[str, ...]:
        """Places a reader should look at that are not errors, such as interior thought in action."""
