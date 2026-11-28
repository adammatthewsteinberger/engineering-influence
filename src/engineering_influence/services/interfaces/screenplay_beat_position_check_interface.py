# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScreenplayBeatPositionCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ScreenplayBeatPositionCheckInterface(ABC):
    """Checks that an assembled script places each beat where the beat sheet puts it."""

    __slots__ = ()

    @abstractmethod
    def problems(self, beat_sheet: str, scenes: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
        """The beats that are missing from the script or fall out of place, given each scene's beat and text in card
        order."""
