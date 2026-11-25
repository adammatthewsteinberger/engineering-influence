# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PhaseRun."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.phase_run import PhaseRun
    from engineering_influence.models.phase_state import PhaseState


class PhaseRunInterface(ABC):
    """A phase run whose transitions are validated before persistence."""

    __slots__ = ()

    @abstractmethod
    def transition(self, target: PhaseState) -> PhaseRun:
        """Return a new run after applying one legal transition."""
