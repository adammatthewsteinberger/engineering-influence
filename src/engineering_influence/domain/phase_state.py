"""Phase-run states."""

from enum import StrEnum


class PhaseState(StrEnum):
    """The durable lifecycle of one pipeline phase."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_GATE = "awaiting_gate"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"
