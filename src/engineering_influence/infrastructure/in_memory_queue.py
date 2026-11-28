# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deterministic in-memory queue for local CLI and tests."""

from engineering_influence.interfaces.queue_interface import QueueInterface


class InMemoryQueue(QueueInterface):
    """Queue adapter that records jobs and returns stable local identifiers."""

    def __init__(self) -> None:
        """Start with no jobs."""
        self.jobs: list[tuple[str, dict[str, object]]] = []

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        """Queue a job of this kind with a copy of its payload, and return its local job id."""
        self.jobs.append((kind, dict(payload)))
        return f"local-job-{len(self.jobs)}"
