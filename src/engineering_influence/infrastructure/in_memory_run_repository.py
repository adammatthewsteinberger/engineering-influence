# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Run repository held in memory, for local demonstrations and tests."""

from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import BookRun


class InMemoryRunRepository(RunRepositoryInterface):
    """Keeps the last saved state of each run in a dictionary."""

    def __init__(self) -> None:
        self._runs: dict[str, BookRun] = {}

    def save(self, run: BookRun) -> None:
        self._runs[run.run_id] = run

    def get(self, run_id: str) -> BookRun | None:
        return self._runs.get(run_id)

    def run_ids(self) -> list[str]:
        return sorted(self._runs)
