# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayToneRatioCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayToneRatioCheckInterface(ABC):
    """The warm-to-conflict ratio of a screenplay's scene cards (prompt 09, the relational arc test)."""

    __slots__ = ()

    @abstractmethod
    def problems(self, text: str) -> tuple[str, ...]:
        """Every bad tone and the ratio problem, or nothing when the tagged cards pass."""
