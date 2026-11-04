"""Phase execution service port."""

from abc import ABC, abstractmethod

from engineering_influence.domain.artifact import Artifact
from engineering_influence.domain.gate import Gate
from engineering_influence.domain.phase_run import PhaseRun


class RunPhaseInterface(ABC):
    """Run one phase and return its artifact and next state."""

    @abstractmethod
    async def run(
        self,
        phase_run: PhaseRun,
        artifact_type: str,
        gate: Gate,
        context: dict[str, object],
    ) -> tuple[PhaseRun, Artifact]:
        """Execute the phase."""
