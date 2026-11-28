# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Moves a book run through its stages, safely under redelivery, retries and crashes."""

import asyncio

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.models.book_run import FINISHED, BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.failure_kind import FailureKind
from engineering_influence.models.outbox_event import OutboxEvent
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.services.interfaces.advance_run_interface import AdvanceRunInterface
from engineering_influence.services.interfaces.failure_classifier_interface import (
    FailureClassifierInterface,
)
from engineering_influence.services.interfaces.run_event_builder_interface import (
    RunEventBuilderInterface,
)
from engineering_influence.services.run_event_builder import RunEventBuilder

DETAIL_LIMIT = 200
# Runs that wait for a person or for credit: an advance message leaves them alone.
WAITING = frozenset({RunStatus.PARKED_CAPACITY, RunStatus.AWAITING_CONSENT})


class AdvanceRun(AdvanceRunInterface):
    """One delivery of ``run.advance`` for a stage: execute it, save the run, queue the next.

    Delivery is at least once, so the stage named in a message is checked against the run:

    * the run's current stage runs;
    * an earlier stage is skipped, because the run already moved past it;
    * the stage just before the current one means a worker saved the advance and died before it
      queued the next stage, so the current stage is queued again (``REPAIRED``);
    * a finished or parked run skips everything, and a later stage is an error.

    Two deliveries of one stage can overlap, so every change to the run is a compare-and-swap
    against the state this delivery read. The delivery that loses reports ``SKIPPED`` and neither
    overwrites the winner nor queues anything, so duplicates cannot compound down the chain.

    The budget's ``spent`` is recomputed from the journal after every attempt, whether it
    succeeded or failed, so a crash cannot lose the cost of a call that happened and a replayed
    call is never counted twice. ``reserved`` is reset to zero on purpose: a reservation lives
    inside one model call and is settled before a stage returns, so a saved run never holds one.
    If the journal records more than the cap, the run fails with a blocking ``budget-exceeded``
    issue rather than raising, so the message is not redelivered forever.
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
        events: RunEventBuilderInterface | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("a stage needs at least one attempt")
        self._runs = runs
        self._events = events if events is not None else RunEventBuilder(())
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
            started = run.start()
            if not await self._swap(run, started, self._events.started(started)):
                return AdvanceOutcome.SKIPPED
            run = started
        try:
            report = await self._executor.execute(run, attempt)
        except Exception as error:  # noqa: BLE001 - every failure is classified, none is dropped
            return await self._failed(run, attempt, error)
        try:
            settled = await self._settled(run)
        except BudgetExceededError:
            return await self._overspent(run)
        for issue in report.issues:
            settled = settled.with_issue(issue)
        advanced = settled.advance()
        if advanced.status is RunStatus.COMPLETED:
            done = self._events.phase_completed(run, run.stage) + self._events.completed(advanced)
            return await self._commit(run, advanced, AdvanceOutcome.COMPLETED, done)
        outcome = await self._commit(
            run, advanced, AdvanceOutcome.ADVANCED, self._events.phase_completed(run, run.stage)
        )
        if outcome is AdvanceOutcome.ADVANCED:
            await self._enqueue(advanced, advanced.stage, 1)
        return outcome

    async def _already_handled(self, run: BookRun, stage: str) -> AdvanceOutcome | None:
        if run.status in FINISHED or run.status in WAITING:
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
        if isinstance(error, SpendConsentNeededError):
            return await self._awaiting_consent(run, error)
        kind = self._classifier.classify(error)
        try:
            settled = await self._settled(run)
        except BudgetExceededError:
            return await self._overspent(run)
        if kind is FailureKind.TRANSIENT and attempt < self._max_attempts:
            outcome = await self._commit(run, settled, AdvanceOutcome.RETRYING)
            if outcome is AdvanceOutcome.RETRYING:
                await self._enqueue(settled, settled.stage, attempt + 1)
            return outcome
        if kind is FailureKind.CAPACITY:
            return await self._commit(run, settled.park(), AdvanceOutcome.PARKED)
        code = "stage-failed" if kind is FailureKind.UNRECOVERABLE else "retries-exhausted"
        detail = f"{type(error).__name__}: {error}"[:DETAIL_LIMIT]
        issue = QualityIssue(stage=run.stage, code=code, detail=detail, blocking=True)
        return await self._commit(
            run,
            settled.with_issue(issue).fail(),
            AdvanceOutcome.FAILED,
            self._events.failed(run, code),
        )

    async def _awaiting_consent(
        self, run: BookRun, error: SpendConsentNeededError
    ) -> AdvanceOutcome:
        """Park the run for a decision: the stage stops here, and the calls it made stay journaled."""
        try:
            settled = await self._settled(run)
        except BudgetExceededError:
            return await self._overspent(run)
        request = SpendRequest(error.requested_micro_usd, run.stage)
        return await self._commit(
            run,
            settled.await_consent(request),
            AdvanceOutcome.AWAITING_CONSENT,
            self._events.awaiting_gate(run, run.stage),
        )

    async def _overspent(self, run: BookRun) -> AdvanceOutcome:
        issue = QualityIssue(
            stage=run.stage,
            code="budget-exceeded",
            detail="the journal records more spend than the run's cap",
            blocking=True,
        )
        return await self._commit(
            run,
            run.with_issue(issue).fail(),
            AdvanceOutcome.FAILED,
            self._events.failed(run, "budget-exceeded"),
        )

    async def _settled(self, run: BookRun) -> BookRun:
        entries = await asyncio.to_thread(self._journal.entries, run.run_id)
        spent = sum(entry.cost_micro_usd for entry in entries)
        return run.with_budget(Budget(cap=run.budget.cap, spent=spent))

    async def _swap(
        self, before: BookRun, after: BookRun, events: tuple[OutboxEvent, ...] = ()
    ) -> bool:
        return await asyncio.to_thread(self._runs.swap_with_events, before, after, events)

    async def _commit(
        self,
        before: BookRun,
        after: BookRun,
        outcome: AdvanceOutcome,
        events: tuple[OutboxEvent, ...] = (),
    ) -> AdvanceOutcome:
        """The outcome if this delivery's change was stored, with its events, SKIPPED if another delivery won."""
        return outcome if await self._swap(before, after, events) else AdvanceOutcome.SKIPPED

    async def _enqueue(self, run: BookRun, stage: str, attempt: int) -> None:
        await asyncio.to_thread(
            self._queue.enqueue,
            self.KIND,
            {"run_id": run.run_id, "stage": stage, "attempt": attempt},
        )
