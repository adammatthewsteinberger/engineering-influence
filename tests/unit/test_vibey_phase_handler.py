"""Vibey phase handler outcome tests."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

from vibey.application.worker import Park, Success

from engineering_influence.infrastructure.vibey_phase_handler import VibeyPhaseHandler
from engineering_influence.interfaces.gate_port import GatePort
from engineering_influence.interfaces.runner_port import RunnerPort


class RunnerFake(RunnerPort):
    """Returns a deterministic artifact."""

    async def run(self, phase: str, context: dict[str, object]) -> str:
        return f"content:{phase}"


class GateFake(GatePort):
    """Returns a configured gate decision."""

    def __init__(self, accepted: bool) -> None:
        self.accepted = accepted

    def evaluate(self, artifact: object) -> bool:
        return self.accepted


def job(kind: str, gate_kind: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        kind=kind,
        payload={
            "artifact_type": "thesis",
            "gate_name": "review",
            "gate_kind": gate_kind,
            "gate_rubric": "review this artifact",
        },
    )


def test_handler_returns_vibey_success_for_accepted_auto_gate() -> None:
    result = asyncio.run(
        VibeyPhaseHandler(RunnerFake(), GateFake(True)).handle(job("thesis.p1", "auto"))
    )

    assert isinstance(result, Success)
    assert result.result["content"] == "content:thesis.p1"


def test_handler_returns_vibey_park_for_human_gate() -> None:
    result = asyncio.run(
        VibeyPhaseHandler(RunnerFake(), GateFake(True)).handle(job("thesis.p1", "human"))
    )

    assert isinstance(result, Park)
    assert result.request.kind == "review"
