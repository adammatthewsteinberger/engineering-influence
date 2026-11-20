# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Moves a book run through its stages, safely under redelivery, retries and crashes."""

import asyncio

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.models.book_run import FINISHED, BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.failure_kind import FailureKind
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.run_status import RunStatus
from engineering_influence.services.interfaces.advance_run_interface import AdvanceRunInterface
from engineering_influence.services.interfaces.failure_classifier_interface import (
    FailureClassifierInterface,
)

DETAIL_LIMIT = 200


class AdvanceRun(AdvanceRunInterface):
    """One delivery of ``run.advance`` for a stage: execute it, save the run, queue the next.

    Delivery is at least once, so the stage named in a message is checked against the run:

    * the run's current stage runs;
    * an earlier stage is skipped, because the run already moved past it;
    * the stage just before the current one means a worker saved the advance and died before it
      queued the next stage, so the current stage is queued again (``REPAIRED``);
    * a finished or parked run skips everything, and a later stage is an error.

    The budget's ``spent`` is recomputed from the journal after every attempt, whether it
    succeeded or failed, so a crash cannot lose the cost of a call that happened and a replayed
    call is never counted twice.
    """

    KIND = "run.advance"

    def __init__(
        self,
        runs: RunRepositoryInterface,
        journal: JournalInterface,
        executor: StageExecutorInterface,
        queue: QueueInterface,
        classifier: FailureClassifierInterface,
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("a stage needs at least one attempt")
        self._runs = runs
        self._journal = journal
        self._executor = executor
        self._queue = queue
        self._classifier = classifier
        self._max_attempts = max_attempts

    async def advance(self, run_id: str, stage: str, attempt: int) -> AdvanceOutcome:
        """Handle one delivery of an advance message for a stage of a run."""
        run = await asyncio.to_thread(self._runs.get, run_id)
        if run is None:
            raise ApplicationError(
                code="RUN_NOT_FOUND", message=f"no run {run_id!r}", http_status=404
            )
        if stage not in run.plan.stages:
            raise ApplicationError(
                code="UNKNOWN_STAGE",
                message=f"{stage!r} is not a stage of run {run_id!r}",
                http_status=422,
            )
        early = await self._already_handled(run, stage)
        if early is not None:
            return early
        if run.status is RunStatus.PENDING:
            run = run.start()
            await asyncio.to_thread(self._runs.save, run)
        try:
            report = await self._executor.execute(run, attempt)
        except Exception as error:  # noqa: BLE001 - every failure is classified, none is dropped
            return await self._failed(run, attempt, error)
        run = await self._settled(run)
        for issue in report.issues:
            run = run.with_issue(issue)
        run = run.advance()
        await asyncio.to_thread(self._runs.save, run)
        if run.status is RunStatus.COMPLETED:
            return AdvanceOutcome.COMPLETED
        await self._enqueue(run, run.stage, 1)
        return AdvanceOutcome.ADVANCED

    async def _already_handled(self, run: BookRun, stage: str) -> AdvanceOutcome | None:
        if run.status in FINISHED or run.status is RunStatus.PARKED_CAPACITY:
            return AdvanceOutcome.SKIPPED
        stages = run.plan.stages
        current, requested = stages.index(run.stage), stages.index(stage)
        if requested > current:
            raise ApplicationError(
                code="STAGE_OUT_OF_ORDER",
                message=f"run {run.run_id!r} is at {run.stage!r}, not {stage!r}",
                http_status=409,
            )
        if requested == current:
            return None
        if requested == current - 1:
            await self._enqueue(run, run.stage, 1)
            return AdvanceOutcome.REPAIRED
        return AdvanceOutcome.SKIPPED

    async def _failed(self, run: BookRun, attempt: int, error: Exception) -> AdvanceOutcome:
        kind = self._classifier.classify(error)
        run = await self._settled(run)
        if kind is FailureKind.TRANSIENT and attempt < self._max_attempts:
            await asyncio.to_thread(self._runs.save, run)
            await self._enqueue(run, run.stage, attempt + 1)
            return AdvanceOutcome.RETRYING
        if kind is FailureKind.CAPACITY:
            await asyncio.to_thread(self._runs.save, run.park())
            return AdvanceOutcome.PARKED
        code = "stage-failed" if kind is FailureKind.UNRECOVERABLE else "retries-exhausted"
        detail = f"{type(error).__name__}: {error}"[:DETAIL_LIMIT]
        issue = QualityIssue(stage=run.stage, code=code, detail=detail, blocking=True)
        await asyncio.to_thread(self._runs.save, run.with_issue(issue).fail())
        return AdvanceOutcome.FAILED

    async def _settled(self, run: BookRun) -> BookRun:
        entries = await asyncio.to_thread(self._journal.entries, run.run_id)
        spent = sum(entry.cost_micro_usd for entry in entries)
        return run.with_budget(Budget(cap=run.budget.cap, spent=spent))

    async def _enqueue(self, run: BookRun, stage: str, attempt: int) -> None:
        await asyncio.to_thread(
            self._queue.enqueue,
            self.KIND,
            {"run_id": run.run_id, "stage": stage, "attempt": attempt},
        )
