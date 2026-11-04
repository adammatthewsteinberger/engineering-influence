# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tracing decorator for the phase-execution service."""

from vibey_bootstrap.tracing.decorators import traced_async

from engineering_influence.domain.artifact import Artifact
from engineering_influence.domain.gate import Gate
from engineering_influence.domain.phase_run import PhaseRun
from engineering_influence.services.interfaces.run_phase_interface import RunPhaseInterface


class TracedRunPhase(RunPhaseInterface):
    """Record latency and errors for every phase; the context holds manuscript text."""

    def __init__(self, inner: RunPhaseInterface) -> None:
        self._inner = inner

    @traced_async(
        operation="service.run_phase",
        sensitive_args=("phase_run", "artifact_type", "gate", "context"),
    )
    async def run(
        self,
        phase_run: PhaseRun,
        artifact_type: str,
        gate: Gate,
        context: dict[str, object],
    ) -> tuple[PhaseRun, Artifact]:
        """Delegate to the wrapped service."""
        return await self._inner.run(phase_run, artifact_type, gate, context)
