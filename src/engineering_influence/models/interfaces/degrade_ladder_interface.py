# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for DegradeLadder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.degrade_ladder import DegradeLadder


class DegradeLadderInterface(ABC):
    """Rungs from best to cheapest; a run steps down one rung at a time, never back up."""

    __slots__ = ()

    @abstractmethod
    def current(self) -> str:
        """The rung the run is on now."""

    @abstractmethod
    def exhausted(self) -> bool:
        """True on the last rung, where there is nothing cheaper to try."""

    @abstractmethod
    def step_down(self) -> DegradeLadder:
        """The ladder one rung lower; stepping off the bottom is an error."""
