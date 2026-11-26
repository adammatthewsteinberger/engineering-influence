# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayBeatSheetCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayBeatSheetCheckInterface(ABC):
    """The mechanical checks on a screenplay's beat sheet (prompt 08, step 8.2.1)."""

    __slots__ = ()

    @abstractmethod
    def problems(self, text: str) -> tuple[str, ...]:
        """Every way the beat sheet breaks the format, or nothing when it passes."""
