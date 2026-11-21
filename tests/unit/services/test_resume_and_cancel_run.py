"""Resuming and cancelling book runs."""

import asyncio
from collections import deque

import pytest

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.interfaces.advance_run_interface import AdvanceRunInterface
from engineering_influence.services.process_run_job import ProcessRunJob
from engineering_influence.services.resume_run import ResumeRun

STAGES = ("brief", "outline", "draft")


def a_run(status: RunStatus = RunStatus.RUNNING, stage: str = "outline") -> BookRun:
    brief = BookBrief(kind=BookKind.NONFICTION, idea="sourdough", budget_micro_usd=1_000)
    plan = StagePlan(kind=BookKind.NONFICTION, stages=STAGES)
    return BookRun("run-1", brief, plan, Budget(cap=1_000), stage=stage, status=status)


def stored(status: RunStatus, stage: str = "outline") -> InMemoryRunRepository:
    runs = InMemoryRunRepository()
    runs.save(a_run(status, stage))
    return runs


class SpyQueue(InMemoryQueue):
    """Records what the run looked like at the moment a job was queued."""

    def __init__(self, runs: InMemoryRunRepository) -> None:
        super().__init__()
        self._runs = runs
        self.status_when_queued: list[RunStatus] = []

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        found = self._runs.get("run-1")
        assert found is not None
        self.status_when_queued.append(found.status)
        return super().enqueue(kind, payload)


class Losing(InMemoryRunRepository):
    """Another worker changes the stored run just before each of the first ``losses`` swaps."""

    def __init__(self, losses: int) -> None:
        super().__init__()
        self.losses = losses
        self.swaps = 0

    def swap(self, expected: BookRun, replacement: BookRun) -> bool:
        self.swaps += 1
        if self.swaps <= self.losses:
            current = self._runs[expected.run_id]
            self._runs[expected.run_id] = (
                current.advance()
                if current.stage != "draft"
                else current.with_budget(Budget(cap=1_000, spent=self.swaps))
            )
        return super().swap(expected, replacement)


# --------------------------------------------------------------- resume


def test_resuming_a_parked_run_makes_it_running_and_queues_its_stage() -> None:
    runs = stored(RunStatus.PARKED_CAPACITY)
    queue = InMemoryQueue()
    resumed = ResumeRun(runs, queue).resume("run-1")
    assert (resumed.status, resumed.stage) == (RunStatus.RUNNING, "outline")
    assert runs.get("run-1") == resumed
    assert queue.jobs == [("run.advance", {"run_id": "run-1", "stage": "outline", "attempt": 1})]


def test_the_run_is_un_parked_before_its_stage_is_queued() -> None:
    runs = stored(RunStatus.PARKED_CAPACITY)
    queue = SpyQueue(runs)
    ResumeRun(runs, queue).resume("run-1")
    assert queue.status_when_queued == [RunStatus.RUNNING]


@pytest.mark.parametrize("status", [RunStatus.RUNNING, RunStatus.PENDING])
def test_resuming_a_run_that_is_not_parked_only_queues_its_stage_again(status: RunStatus) -> None:
    runs = stored(status)
    queue = InMemoryQueue()
    before = runs.get("run-1")
    result = ResumeRun(runs, queue).resume("run-1")
    assert result == before == runs.get("run-1")
    assert [job[1]["stage"] for job in queue.jobs] == ["outline"]


@pytest.mark.parametrize("status", [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED])
def test_a_finished_run_cannot_be_resumed(status: RunStatus) -> None:
    queue = InMemoryQueue()
    with pytest.raises(ApplicationError) as raised:
        ResumeRun(stored(status), queue).resume("run-1")
    assert (raised.value.code, raised.value.http_status) == ("RUN_FINISHED", 409)
    assert status.value in raised.value.message
    assert queue.jobs == []


def test_resuming_a_run_that_does_not_exist_is_a_404() -> None:
    with pytest.raises(ApplicationError) as raised:
        ResumeRun(InMemoryRunRepository(), InMemoryQueue()).resume("nope")
    assert (raised.value.code, raised.value.http_status) == ("RUN_NOT_FOUND", 404)


def test_a_resume_that_loses_the_race_says_to_try_again_and_queues_nothing() -> None:
    runs = Losing(losses=1)
    runs.save(a_run(RunStatus.PARKED_CAPACITY))
    queue = InMemoryQueue()
    with pytest.raises(ApplicationError) as raised:
        ResumeRun(runs, queue).resume("run-1")
    assert (raised.value.code, raised.value.retryable) == ("RUN_CHANGED", True)
    assert queue.jobs == []


def test_a_resume_queues_exactly_what_the_worker_accepts() -> None:
    class Advancer(AdvanceRunInterface):
        def __init__(self) -> None:
            self.calls: list[tuple[str, str, int]] = []

        async def advance(self, run_id: str, stage: str, attempt: int) -> AdvanceOutcome:
            self.calls.append((run_id, stage, attempt))
            return AdvanceOutcome.ADVANCED

    queue = InMemoryQueue()
    ResumeRun(stored(RunStatus.PARKED_CAPACITY, "draft"), queue).resume("run-1")
    kind, payload = queue.jobs[0]
    advancer = Advancer()
    message = JobMessage(job_id="job-1", kind=kind, payload=payload)
    asyncio.run(ProcessRunJob(advancer).process(message))
    assert advancer.calls == [("run-1", "draft", 1)]


class CreditThenFine(StageExecutorInterface):
    """Runs out of credit on its first call, then works."""

    def __init__(self) -> None:
        self.script: deque[bool] = deque([True])
        self.calls = 0

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        self.calls += 1
        if self.script and self.script.popleft():
            raise CapacityExhaustedError("credit exhausted")
        return StageReport()


def test_a_run_parked_for_credit_finishes_after_it_is_resumed() -> None:
    runs = InMemoryRunRepository()
    runs.save(
        BookRun(
            "run-1",
            a_run().brief,
            StagePlan(kind=BookKind.NONFICTION, stages=("only",)),
            Budget(cap=1_000),
        )
    )
    queue = InMemoryQueue()
    advance = AdvanceRun(runs, InMemoryJournal(), CreditThenFine(), queue, FailureClassifier())
    assert asyncio.run(advance.advance("run-1", "only", 1)) is AdvanceOutcome.PARKED
    assert asyncio.run(advance.advance("run-1", "only", 1)) is AdvanceOutcome.SKIPPED

    ResumeRun(runs, queue).resume("run-1")
    assert asyncio.run(advance.advance("run-1", "only", 1)) is AdvanceOutcome.COMPLETED
    final = runs.get("run-1")
    assert final is not None and final.status is RunStatus.COMPLETED


# --------------------------------------------------------------- cancel


@pytest.mark.parametrize(
    "status", [RunStatus.PENDING, RunStatus.RUNNING, RunStatus.PARKED_CAPACITY]
)
def test_an_unfinished_run_can_be_cancelled(status: RunStatus) -> None:
    runs = stored(status)
    cancelled = CancelRun(runs).cancel("run-1")
    assert cancelled.status is RunStatus.CANCELLED
    assert runs.get("run-1") == cancelled
    assert cancelled.stage == "outline"


def test_cancelling_twice_changes_nothing() -> None:
    runs = stored(RunStatus.CANCELLED)
    before = runs.get("run-1")
    assert CancelRun(runs).cancel("run-1") == before
    assert runs.get("run-1") == before


@pytest.mark.parametrize("status", [RunStatus.COMPLETED, RunStatus.FAILED])
def test_a_run_that_completed_or_failed_cannot_be_cancelled(status: RunStatus) -> None:
    with pytest.raises(ApplicationError) as raised:
        CancelRun(stored(status)).cancel("run-1")
    assert (raised.value.code, raised.value.http_status) == ("RUN_FINISHED", 409)


def test_cancelling_a_run_that_does_not_exist_is_a_404() -> None:
    with pytest.raises(ApplicationError) as raised:
        CancelRun(InMemoryRunRepository()).cancel("nope")
    assert (raised.value.code, raised.value.http_status) == ("RUN_NOT_FOUND", 404)


def test_a_cancel_that_loses_to_an_advance_reads_the_run_again_and_wins() -> None:
    runs = Losing(losses=1)
    runs.save(a_run(RunStatus.RUNNING, "brief"))
    cancelled = CancelRun(runs).cancel("run-1")
    assert cancelled.status is RunStatus.CANCELLED
    assert cancelled.stage == "outline"  # the advance that won the first round is kept
    assert runs.swaps == 2


def test_a_run_that_keeps_changing_is_reported_after_a_few_tries() -> None:
    runs = Losing(losses=99)
    runs.save(a_run(RunStatus.RUNNING, "brief"))
    with pytest.raises(ApplicationError) as raised:
        CancelRun(runs).cancel("run-1")
    assert (raised.value.code, raised.value.retryable) == ("RUN_CHANGED", True)
    assert runs.swaps == CancelRun.ATTEMPTS


class CancelsMidStage(StageExecutorInterface):
    """Someone cancels the run while the stage is executing."""

    def __init__(self, runs: InMemoryRunRepository) -> None:
        self.runs = runs

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        CancelRun(self.runs).cancel(run.run_id)
        return StageReport()


def test_a_cancel_during_a_stage_sticks_and_nothing_further_is_queued() -> None:
    runs = InMemoryRunRepository()
    runs.save(a_run(RunStatus.RUNNING, "brief"))
    queue = InMemoryQueue()
    advance = AdvanceRun(runs, InMemoryJournal(), CancelsMidStage(runs), queue, FailureClassifier())
    assert asyncio.run(advance.advance("run-1", "brief", 1)) is AdvanceOutcome.SKIPPED
    final = runs.get("run-1")
    assert final is not None
    assert (final.status, final.stage) == (RunStatus.CANCELLED, "brief")
    assert queue.jobs == []
