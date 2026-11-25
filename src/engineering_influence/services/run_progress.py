# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a run's last saved state, for a client that follows its progress."""

from __future__ import annotations

from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.services.interfaces.run_progress_interface import RunProgressInterface


class RunProgress(RunProgressInterface):
    """Read-only: the worker saves every stage's outcome, and this only reads what was saved."""

    def __init__(self, runs: RunRepositoryInterface) -> None:
        self._runs = runs

    def current(self, run_id: str) -> BookRun | None:
        """The run as it was last saved, or None."""
        return self._runs.get(run_id)
