# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Grants or denies a run's request for more budget."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.interfaces.resolve_spend_consent_interface import (
    ResolveSpendConsentInterface,
)
from engineering_influence.services.interfaces.spend_ceiling_interface import (
    SpendCeilingInterface,
)


class ResolveSpendConsent(ResolveSpendConsentInterface):
    """A grant raises the cap and queues the stage (once the spend ceiling, if there is one, allows the raise); a denial parks the run and queues nothing.

    Both are a compare-and-swap against the state that was read, so an answer that races another
    one is refused (RUN_CHANGED) rather than applied twice.
    """

    def __init__(
        self,
        runs: RunRepositoryInterface,
        queue: QueueInterface,
        ceiling: SpendCeilingInterface | None = None,
    ) -> None:
        self._runs = runs
        self._queue = queue
        self._ceiling = ceiling

    def grant(self, run_id: str, micro_usd: int | None = None) -> BookRun:
        """Raise the cap, un-park the run, and queue its current stage."""
        run = self._load(run_id)
        try:
            changed = run.grant(micro_usd)
        except ValueError as error:
            raise ApplicationError(
                code="CONSENT_NOT_PENDING", message=str(error), http_status=409
            ) from error
        if self._ceiling is not None:
            self._ceiling.admit_raise(run, changed.budget.cap - run.budget.cap)
        self._store(run, changed)
        self._queue.enqueue(
            AdvanceRun.KIND, {"run_id": run_id, "stage": changed.stage, "attempt": 1}
        )
        return changed

    def deny(self, run_id: str) -> BookRun:
        """Park the run, so it stays until it is granted more budget."""
        run = self._load(run_id)
        try:
            changed = run.deny()
        except ValueError as error:
            raise ApplicationError(
                code="CONSENT_NOT_PENDING", message=str(error), http_status=409
            ) from error
        self._store(run, changed)
        return changed

    def _load(self, run_id: str) -> BookRun:
        run = self._runs.get(run_id)
        if run is None:
            raise ApplicationError(
                code="RUN_NOT_FOUND", message=f"no run {run_id!r}", http_status=404
            )
        return run

    def _store(self, before: BookRun, after: BookRun) -> None:
        if not self._runs.swap(before, after):
            raise ApplicationError(
                code="RUN_CHANGED",
                message=f"run {before.run_id!r} changed while it was being answered; try again",
                http_status=409,
                retryable=True,
            )
