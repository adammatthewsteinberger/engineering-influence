# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gets a parked or stalled book run moving again."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import FINISHED, BookRun
from engineering_influence.models.run_status import RunStatus
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.interfaces.resume_run_interface import ResumeRunInterface


class ResumeRun(ResumeRunInterface):
    """A parked run is moved to running, then its current stage is queued.

    The queueing comes second, because a message that arrives while the run is still parked is
    skipped. Resuming a run that is already running only queues its stage again, so a resume
    that died between the two steps is repaired by running it once more, and a duplicate
    message is harmless: ``AdvanceRun`` skips whatever it has already done.
    """

    def __init__(self, runs: RunRepositoryInterface, queue: QueueInterface) -> None:
        """Remember the run repository and queue the resumed stage goes to."""
        self._runs = runs
        self._queue = queue

    def resume(self, run_id: str) -> BookRun:
        """Un-park the run if it is parked, queue its current stage, and return it."""
        run = self._runs.get(run_id)
        if run is None:
            raise ApplicationError(
                code="RUN_NOT_FOUND", message=f"no run {run_id!r}", http_status=404
            )
        if run.status in FINISHED:
            raise ApplicationError(
                code="RUN_FINISHED",
                message=f"run {run_id!r} is already {run.status.value}",
                http_status=409,
            )
        if run.status is RunStatus.PARKED_CAPACITY:
            resumed = run.resume()
            if not self._runs.swap(run, resumed):
                raise ApplicationError(
                    code="RUN_CHANGED",
                    message=f"run {run_id!r} changed while it was being resumed; try again",
                    http_status=409,
                    retryable=True,
                )
            run = resumed
        self._queue.enqueue(
            AdvanceRun.KIND, {"run_id": run.run_id, "stage": run.stage, "attempt": 1}
        )
        return run
