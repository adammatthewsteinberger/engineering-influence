# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Phase execution service port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.artifact import Artifact
    from engineering_influence.models.gate import Gate
    from engineering_influence.models.phase_run import PhaseRun


class RunPhaseInterface(ABC):
    """Run one phase and return its artifact and next state."""

    __slots__ = ()

    @abstractmethod
    async def run(
        self,
        phase_run: PhaseRun,
        artifact_type: str,
        gate: Gate,
        context: dict[str, object],
    ) -> tuple[PhaseRun, Artifact]:
        """Execute the phase."""
