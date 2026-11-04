"""State-machine tests for the initial domain."""

import pytest

from engineering_influence.domain import PhaseRun, PhaseState


def test_pending_run_can_be_queued() -> None:
    run = PhaseRun("r1", "thesis")
    assert run.transition(PhaseState.QUEUED).state is PhaseState.QUEUED


def test_completed_run_cannot_be_reopened() -> None:
    run = PhaseRun("r1", "thesis").transition(PhaseState.QUEUED)
    run = run.transition(PhaseState.RUNNING).transition(PhaseState.COMPLETED)
    with pytest.raises(ValueError, match="illegal phase transition"):
        run.transition(PhaseState.QUEUED)
