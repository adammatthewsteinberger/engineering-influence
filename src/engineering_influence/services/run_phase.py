# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Application service for running a phase and applying its first gate."""

from engineering_influence.domain.artifact import Artifact
from engineering_influence.domain.gate import Gate
from engineering_influence.domain.gate_kind import GateKind
from engineering_influence.domain.phase_run import PhaseRun
from engineering_influence.interfaces.gate_port import GatePort
from engineering_influence.interfaces.runner_port import RunnerPort
from engineering_influence.services.interfaces.run_phase_interface import RunPhaseInterface


class RunPhase(RunPhaseInterface):
    """Run one phase through an injected runner and gate evaluator."""

    def __init__(self, runner: RunnerPort, gates: GatePort) -> None:
        self._runner = runner
        self._gates = gates

    async def run(
        self,
        phase_run: PhaseRun,
        artifact_type: str,
        gate: Gate,
        context: dict[str, object],
    ) -> tuple[PhaseRun, Artifact]:
        """Return the produced artifact and its next legal run state."""
        running = phase_run.transition(phase_run.state.RUNNING)
        content = await self._runner.run(running.phase, context)
        artifact = Artifact(f"{running.run_id}:{running.phase}", artifact_type, content, gate)
        if gate.kind is GateKind.AUTO and self._gates.evaluate(artifact):
            return running.transition(running.state.COMPLETED), artifact
        return running.transition(running.state.AWAITING_GATE), artifact
