# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The pure phase-run state machine."""

from dataclasses import dataclass

from engineering_influence.domain.phase_state import PhaseState


@dataclass(frozen=True, slots=True)
class PhaseRun:
    """A phase run whose transitions are validated before persistence."""

    run_id: str
    phase: str
    state: PhaseState = PhaseState.PENDING

    def transition(self, target: PhaseState) -> "PhaseRun":
        """Return a new run after applying one legal transition."""
        allowed = {
            PhaseState.PENDING: {PhaseState.QUEUED, PhaseState.FAILED},
            PhaseState.QUEUED: {PhaseState.RUNNING, PhaseState.FAILED, PhaseState.DEAD_LETTERED},
            PhaseState.RUNNING: {
                PhaseState.AWAITING_GATE,
                PhaseState.COMPLETED,
                PhaseState.FAILED,
                PhaseState.DEAD_LETTERED,
            },
            PhaseState.AWAITING_GATE: {PhaseState.APPROVED, PhaseState.REJECTED},
            PhaseState.APPROVED: {PhaseState.COMPLETED, PhaseState.FAILED},
            PhaseState.REJECTED: {PhaseState.QUEUED, PhaseState.FAILED},
            PhaseState.COMPLETED: set(),
            PhaseState.FAILED: {PhaseState.QUEUED, PhaseState.DEAD_LETTERED},
            PhaseState.DEAD_LETTERED: set(),
        }
        if target not in allowed[self.state]:
            raise ValueError(f"illegal phase transition: {self.state} -> {target}")
        return PhaseRun(run_id=self.run_id, phase=self.phase, state=target)
