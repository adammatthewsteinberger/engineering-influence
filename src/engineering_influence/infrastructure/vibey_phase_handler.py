"""Vibey worker handler for one engineering-influence phase."""

from importlib import import_module
from typing import Any

from engineering_influence.domain.gate import Gate
from engineering_influence.domain.gate_kind import GateKind
from engineering_influence.domain.phase_run import PhaseRun
from engineering_influence.domain.phase_state import PhaseState
from engineering_influence.interfaces.gate_port import GatePort
from engineering_influence.interfaces.phase_handler_port import PhaseHandlerPort
from engineering_influence.interfaces.runner_port import RunnerPort
from engineering_influence.services.run_phase import RunPhase


class VibeyPhaseHandler(PhaseHandlerPort):
    """Translate vibey job payloads into the shared phase service."""

    def __init__(self, runner: RunnerPort, gates: GatePort) -> None:
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
