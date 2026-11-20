"""Phase runner and gate orchestration tests."""

import asyncio

import pytest

from engineering_influence.interfaces.gate_evaluator_interface import GateEvaluatorInterface
from engineering_influence.interfaces.runner_interface import RunnerInterface
from engineering_influence.models.gate import Gate
from engineering_influence.models.gate_kind import GateKind
from engineering_influence.models.phase_run import PhaseRun
from engineering_influence.models.phase_state import PhaseState
from engineering_influence.services.run_phase import RunPhase


class RunnerFake(RunnerInterface):
    """Returns deterministic phase content."""

    async def run(self, phase: str, context: dict[str, object]) -> str:
        return f"{phase}:{context['project_slug']}"


class GateFake(GateEvaluatorInterface):
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
