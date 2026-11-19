# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Vibey worker handler for one engineering-influence phase."""

from importlib import import_module
from typing import Any

from engineering_influence.interfaces.gate_interface import GateInterface
from engineering_influence.interfaces.phase_handler_interface import PhaseHandlerInterface
from engineering_influence.interfaces.runner_interface import RunnerInterface
from engineering_influence.models.gate import Gate
from engineering_influence.models.gate_kind import GateKind
from engineering_influence.models.phase_run import PhaseRun
from engineering_influence.models.phase_state import PhaseState
from engineering_influence.services.run_phase import RunPhase


class VibeyPhaseHandler(PhaseHandlerInterface):
    """Translate vibey job payloads into the shared phase service."""

    def __init__(self, runner: RunnerInterface, gates: GateInterface) -> None:
        self._phase = RunPhase(runner, gates)

    async def handle(self, job: Any) -> Any:
        """Run a job and return vibey's Success or Park outcome."""
        dto_module = import_module("vibey.application.dto")
        worker_module = import_module("vibey.application.worker")

        payload = dict(job.payload)
        gate = Gate(
            str(payload["gate_name"]),
            GateKind(str(payload["gate_kind"])),
            str(payload["gate_rubric"]),
        )
        next_run, artifact = await self._phase.run(
            PhaseRun(str(job.id), job.kind, PhaseState.QUEUED),
            str(payload["artifact_type"]),
            gate,
            payload,
        )
        if next_run.state is PhaseState.AWAITING_GATE:
            return worker_module.Park(dto_module.HumanGateRequest(gate.name, gate.rubric))
        return worker_module.Success(
            {"artifact_id": artifact.artifact_id, "content": artifact.content}
        )
