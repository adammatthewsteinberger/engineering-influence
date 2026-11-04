"""Deterministic in-memory queue for local CLI and tests."""

from engineering_influence.interfaces.queue_port import QueuePort


class InMemoryQueue(QueuePort):
    """Queue adapter that records jobs and returns stable local identifiers."""

    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict[str, object]]] = []

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        self.jobs.append((kind, dict(payload)))
        return f"local-job-{len(self.jobs)}"
