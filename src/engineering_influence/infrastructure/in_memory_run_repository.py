# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Run repository held in memory, for local demonstrations and tests."""

from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.outbox_event import OutboxEvent


class InMemoryRunRepository(RunRepositoryInterface):
    """Keeps the last saved state of each run in a dictionary, and the events queued with it."""

    def __init__(self) -> None:
        """Start with no runs and no queued events."""
        self._runs: dict[str, BookRun] = {}
        self._events: dict[str, OutboxEvent] = {}

    def save(self, run: BookRun) -> None:
        """Save the run, replacing any saved under the same id."""
        self._runs[run.run_id] = run

    def save_with_events(self, run: BookRun, events: tuple[OutboxEvent, ...]) -> None:
        """Save the run, and queue each event whose key has not been queued before."""
        self._runs[run.run_id] = run
        for event in events:
            self._events.setdefault(event.record_key(), event)

    def queued(self) -> tuple[OutboxEvent, ...]:
        """Every event queued so far, in the order its id was first seen."""
        return tuple(self._events.values())

    def swap(self, expected: BookRun, replacement: BookRun) -> bool:
        """Replace the saved run with the replacement only if it is still the expected run; return whether it was replaced."""
        if replacement.run_id != expected.run_id:
            raise ValueError("a swap cannot change the run id")
        if self._runs.get(expected.run_id) != expected:
            return False
        self._runs[replacement.run_id] = replacement
        return True

    def swap_with_events(
        self, expected: BookRun, replacement: BookRun, events: tuple[OutboxEvent, ...]
    ) -> bool:
        """With no transaction to share in memory, the swap is made first and the events follow only if it stored."""
        if not self.swap(expected, replacement):
            return False
        for event in events:
            self._events.setdefault(event.record_key(), event)
        return True

    def get(self, run_id: str) -> BookRun | None:
        """The saved run with this id, or None."""
        return self._runs.get(run_id)

    def run_ids(self) -> list[str]:
        """The ids of every saved run, sorted."""
        return sorted(self._runs)
