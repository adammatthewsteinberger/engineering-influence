"""Phase runner and gate orchestration tests."""

import asyncio

import pytest

from engineering_influence.domain.gate import Gate
from engineering_influence.domain.gate_kind import GateKind
from engineering_influence.domain.phase_run import PhaseRun
from engineering_influence.domain.phase_state import PhaseState
from engineering_influence.interfaces.gate_port import GatePort
from engineering_influence.interfaces.runner_port import RunnerPort
from engineering_influence.services.run_phase import RunPhase


class RunnerFake(RunnerPort):
    """Returns deterministic phase content."""

    async def run(self, phase: str, context: dict[str, object]) -> str:
        return f"{phase}:{context['project_slug']}"


class GateFake(GatePort):
    """Returns a configured automatic-gate decision."""

    def __init__(self, accepted: bool) -> None:
        self.accepted = accepted

    def evaluate(self, artifact: object) -> bool:
        return self.accepted


def test_auto_gate_completes_accepted_phase() -> None:
    result, artifact = asyncio.run(
        RunPhase(RunnerFake(), GateFake(True)).run(
            PhaseRun("run-1", "thesis.p1", PhaseState.QUEUED),
            "thesis",
            Gate("thesis", GateKind.AUTO, "must be falsifiable"),
            {"project_slug": "demo"},
        )
    )

    assert result.state is PhaseState.COMPLETED
    assert artifact.content == "thesis.p1:demo"


@pytest.mark.parametrize("kind,accepted", [(GateKind.AUTO, False), (GateKind.HUMAN, False)])
def test_unaccepted_or_human_gate_awaits_resolution(kind: GateKind, accepted: bool) -> None:
    result, _artifact = asyncio.run(
        RunPhase(RunnerFake(), GateFake(accepted)).run(
            PhaseRun("run-2", "book.p4", PhaseState.QUEUED),
            "book",
            Gate("review", kind, "review required"),
            {"project_slug": "demo"},
        )
    )

    assert result.state is PhaseState.AWAITING_GATE
