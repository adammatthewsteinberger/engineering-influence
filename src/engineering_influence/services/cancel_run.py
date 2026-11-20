# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Stops a book run for good."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import FINISHED, BookRun
from engineering_influence.models.run_status import RunStatus
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface


class CancelRun(CancelRunInterface):
    """Cancelling twice is fine; cancelling a run that completed or failed is refused.

    A worker may advance the run while the cancel is in flight, which makes the swap lose, so the
    run is read and swapped again a few times before giving up. A stage already executing is not
    interrupted, but its result cannot be stored: the worker's own swap loses to the cancel, so the
    run stays cancelled and nothing further is queued.
    """

    ATTEMPTS = 5

    def __init__(self, runs: RunRepositoryInterface) -> None:
        self._runs = runs

    def cancel(self, run_id: str) -> BookRun:
        """Mark the run cancelled and return it."""
        for _ in range(self.ATTEMPTS):
            run = self._runs.get(run_id)
            if run is None:
                raise ApplicationError(
                    code="RUN_NOT_FOUND", message=f"no run {run_id!r}", http_status=404
                )
            if run.status is RunStatus.CANCELLED:
                return run
            if run.status in FINISHED:
                raise ApplicationError(
                    code="RUN_FINISHED",
                    message=f"run {run_id!r} is already {run.status.value}",
                    http_status=409,
                )
            cancelled = run.cancel()
            if self._runs.swap(run, cancelled):
                return cancelled
        raise ApplicationError(
            code="RUN_CHANGED",
            message=f"run {run_id!r} kept changing while it was being cancelled; try again",
            http_status=409,
            retryable=True,
        )
