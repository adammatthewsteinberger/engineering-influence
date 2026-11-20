"""AdvanceRun: a run moves one stage at a time, and every redelivery, retry and crash is safe."""

import asyncio
from collections import deque

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.failure_kind import FailureKind
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.failure_classifier import FailureClassifier

STAGES = ("brief", "outline", "draft", "package")
CAP = 5_000_000
COST = 100


def new_run(run_id: str = "run-1") -> BookRun:
    brief = BookBrief(kind=BookKind.NONFICTION, idea="sourdough", budget_micro_usd=CAP)
    return BookRun(
        run_id=run_id,
        brief=brief,
        plan=StagePlan(kind=BookKind.NONFICTION, stages=STAGES),
        budget=Budget(cap=CAP),
    )


class Executor(StageExecutorInterface):
    """Does idempotent work for a stage, then does whatever the test scripted for the call."""

    def __init__(
        self,
        journal: InMemoryJournal,
        store: InMemoryArtifactStore,
        script: list[object] | None = None,
    ) -> None:
        self.journal = journal
        self.store = store
        self.script: deque[object] = deque(script or [])
        self.calls: list[tuple[str, int]] = []

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        self.calls.append((run.stage, attempt))
        key = JournalKey("m-1", "p", "v1", run.stage)
        self.journal.record(
            JournalEntry(run.run_id, run.stage, attempt, key, f"text for {run.stage}", COST)
        )
        self.store.put(run.run_id, f"{run.stage}.txt", f"output of {run.stage}".encode())
        step = self.script.popleft() if self.script else None
        if isinstance(step, BaseException):
            raise step
        return step if isinstance(step, StageReport) else StageReport()


class World:
    """Everything a service needs, wired to in-memory fakes."""

    def __init__(self, script: list[object] | None = None, max_attempts: int = 3) -> None:
        self.runs = InMemoryRunRepository()
        self.journal = InMemoryJournal()
        self.store = InMemoryArtifactStore()
        self.queue = InMemoryQueue()
        self.executor = Executor(self.journal, self.store, script)
        self.service = AdvanceRun(
            self.runs, self.journal, self.executor, self.queue, FailureClassifier(), max_attempts
        )
        self.runs.save(new_run())

    def advance(self, stage: str, attempt: int = 1) -> AdvanceOutcome:
        return asyncio.run(self.service.advance("run-1", stage, attempt))

    def run(self) -> BookRun:
        stored = self.runs.get("run-1")
        assert stored is not None
        return stored


def test_a_run_walks_every_stage_and_completes() -> None:
    world = World()
    outcomes = [world.advance(stage) for stage in STAGES]
    assert outcomes == [AdvanceOutcome.ADVANCED] * 3 + [AdvanceOutcome.COMPLETED]
    assert world.run().status is RunStatus.COMPLETED
    assert [job[1]["stage"] for job in world.queue.jobs] == ["outline", "draft", "package"]
    assert {job[0] for job in world.queue.jobs} == {"run.advance"}
    assert world.store.names("run-1") == [f"{stage}.txt" for stage in sorted(STAGES)]


def test_the_first_stage_marks_a_pending_run_as_running() -> None:
    world = World()
    assert world.run().status is RunStatus.PENDING
    world.advance("brief")
    assert world.run().status is RunStatus.RUNNING


def test_the_next_stage_is_queued_for_its_first_attempt() -> None:
    world = World()
    world.advance("brief")
    assert world.queue.jobs == [
        ("run.advance", {"run_id": "run-1", "stage": "outline", "attempt": 1})
    ]


def test_issues_a_stage_reports_are_kept_on_the_run() -> None:
    issue = QualityIssue(stage="brief", code="thin", detail="short idea")
    world = World([StageReport(issues=(issue,))])
    world.advance("brief")
    assert world.run().issues == (issue,)


def test_spend_is_the_sum_of_what_the_journal_recorded() -> None:
    world = World()
    for stage in STAGES[:3]:
        world.advance(stage)
    budget = world.run().budget
    assert (budget.spent, budget.reserved, budget.cap) == (3 * COST, 0, CAP)


def test_a_missing_run_is_an_error() -> None:
    with pytest.raises(ApplicationError) as raised:
        asyncio.run(World().service.advance("nope", "brief", 1))
    assert (raised.value.code, raised.value.http_status) == ("RUN_NOT_FOUND", 404)


def test_a_stage_the_plan_does_not_have_is_an_error() -> None:
    with pytest.raises(ApplicationError) as raised:
        World().advance("typeset")
    assert (raised.value.code, raised.value.http_status) == ("UNKNOWN_STAGE", 422)


def test_a_stage_ahead_of_the_run_is_an_error() -> None:
    world = World()
    with pytest.raises(ApplicationError) as raised:
        world.advance("draft")
    assert (raised.value.code, raised.value.http_status) == ("STAGE_OUT_OF_ORDER", 409)
    assert world.executor.calls == []


def test_a_message_for_a_stage_long_finished_is_skipped() -> None:
    world = World()
    world.advance("brief")
    world.advance("outline")
    calls = len(world.executor.calls)
    queued = len(world.queue.jobs)
    assert world.advance("brief") is AdvanceOutcome.SKIPPED
    assert (len(world.executor.calls), len(world.queue.jobs)) == (calls, queued)


def test_a_redelivered_message_after_a_lost_enqueue_queues_the_current_stage_again() -> None:
    world = World()
    world.advance("brief")
    world.queue.jobs.clear()
    assert world.advance("brief") is AdvanceOutcome.REPAIRED
    assert world.queue.jobs == [
        ("run.advance", {"run_id": "run-1", "stage": "outline", "attempt": 1})
    ]
    assert world.executor.calls == [("brief", 1)]


def test_a_finished_run_skips_every_message() -> None:
    world = World()
    for stage in STAGES:
        world.advance(stage)
    calls = len(world.executor.calls)
    assert world.advance("package") is AdvanceOutcome.SKIPPED
    assert len(world.executor.calls) == calls


def test_a_transient_failure_retries_the_same_stage_with_the_next_attempt() -> None:
    world = World([TransientStageError("rate limited")])
    assert world.advance("brief") is AdvanceOutcome.RETRYING
    assert world.run().stage == "brief"
    assert world.queue.jobs == [
        ("run.advance", {"run_id": "run-1", "stage": "brief", "attempt": 2})
    ]
    assert world.advance("brief", attempt=2) is AdvanceOutcome.ADVANCED


@pytest.mark.parametrize("error", [TimeoutError("slow"), ConnectionError("dropped")])
def test_a_timeout_or_a_dropped_connection_is_transient_too(error: Exception) -> None:
    assert World([error]).advance("brief") is AdvanceOutcome.RETRYING


def test_a_stage_that_keeps_failing_ends_the_run_after_its_last_attempt() -> None:
    world = World([TransientStageError("busy")] * 3, max_attempts=3)
    assert world.advance("brief", 1) is AdvanceOutcome.RETRYING
    assert world.advance("brief", 2) is AdvanceOutcome.RETRYING
    assert world.advance("brief", 3) is AdvanceOutcome.FAILED
    run = world.run()
    assert run.status is RunStatus.FAILED
    assert [(i.code, i.blocking, i.stage) for i in run.issues] == [
        ("retries-exhausted", True, "brief")
    ]
    assert run.has_blocking_issue()


def test_running_out_of_credit_parks_the_run_on_the_same_stage() -> None:
    world = World([CapacityExhaustedError("credit exhausted")])
    assert world.advance("brief") is AdvanceOutcome.PARKED
    run = world.run()
    assert (run.status, run.stage, run.issues) == (RunStatus.PARKED_CAPACITY, "brief", ())
    assert world.queue.jobs == []


def test_a_parked_run_ignores_messages_until_it_is_resumed() -> None:
    world = World([CapacityExhaustedError("credit exhausted")])
    world.advance("brief")
    assert world.advance("brief") is AdvanceOutcome.SKIPPED
    world.runs.save(world.run().resume())
    assert world.advance("brief") is AdvanceOutcome.ADVANCED
    assert world.run().stage == "outline"


def test_an_unknown_failure_ends_the_run_and_records_what_went_wrong() -> None:
    world = World([ValueError("the outline is empty")])
    assert world.advance("brief") is AdvanceOutcome.FAILED
    run = world.run()
    assert run.status is RunStatus.FAILED
    assert [(i.code, i.detail) for i in run.issues] == [
        ("stage-failed", "ValueError: the outline is empty")
    ]


def test_a_very_long_failure_message_is_cut_down() -> None:
    world = World([ValueError("x" * 1000)])
    world.advance("brief")
    assert len(world.run().issues[0].detail) == 200


def test_the_cost_of_a_failed_attempt_is_still_counted() -> None:
    world = World([TransientStageError("busy")])
    world.advance("brief")
    assert world.run().budget.spent == COST


def test_a_stage_needs_at_least_one_attempt() -> None:
    with pytest.raises(ValueError, match="at least one attempt"):
        World(max_attempts=0)


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (CapacityExhaustedError("x"), FailureKind.CAPACITY),
        (TransientStageError("x"), FailureKind.TRANSIENT),
        (TimeoutError("x"), FailureKind.TRANSIENT),
        (ConnectionResetError("x"), FailureKind.TRANSIENT),
        (ValueError("x"), FailureKind.UNRECOVERABLE),
        (KeyError("x"), FailureKind.UNRECOVERABLE),
    ],
)
def test_failures_are_sorted_into_retry_park_or_stop(
    error: BaseException, kind: FailureKind
) -> None:
    assert FailureClassifier().classify(error) is kind


class SimulatedCrash(Exception):
    """The worker process dies at this point."""


class FlakyRuns(InMemoryRunRepository):
    """Loses the nth save by crashing before it is stored."""

    def __init__(self, crash_on: int) -> None:
        super().__init__()
        self.crash_on = crash_on
        self.saves = 0

    def save(self, run: BookRun) -> None:
        self.saves += 1
        if self.saves == self.crash_on:
            raise SimulatedCrash
        super().save(run)


class FlakyQueue(InMemoryQueue):
    """Crashes on the nth enqueue, before the message is recorded."""

    def __init__(self, crash_on: int) -> None:
        super().__init__()
        self.crash_on = crash_on
        self.enqueues = 0

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        self.enqueues += 1
        if self.enqueues == self.crash_on:
            raise SimulatedCrash
        return super().enqueue(kind, payload)


def deliver_until_done(service: AdvanceRun, queue: InMemoryQueue, first: dict[str, object]) -> int:
    """A broker that redelivers a message whenever the worker crashes before acknowledging it."""
    inbox: deque[dict[str, object]] = deque([first])
    deliveries = 0
    while inbox:
        deliveries += 1
        assert deliveries < 40, "the run never settled"
        message = inbox.popleft()
        try:
            asyncio.run(
                service.advance(
                    str(message["run_id"]), str(message["stage"]), int(str(message["attempt"]))
                )
            )
        except SimulatedCrash:
            inbox.appendleft(message)
            continue
        inbox.extend(payload for _, payload in queue.jobs)
        queue.jobs.clear()
    return deliveries


@pytest.mark.parametrize("crash_save", [0, 1, 2, 3, 4, 5])
@pytest.mark.parametrize("crash_enqueue", [0, 1, 2, 3])
def test_a_worker_killed_at_any_point_still_finishes_the_run_with_exact_spend(
    crash_save: int, crash_enqueue: int
) -> None:
    runs = FlakyRuns(crash_on=crash_save)
    queue = FlakyQueue(crash_on=crash_enqueue)
    journal = InMemoryJournal()
    store = InMemoryArtifactStore()
    executor = Executor(journal, store)
    service = AdvanceRun(runs, journal, executor, queue, FailureClassifier())
    InMemoryRunRepository.save(runs, new_run())

    deliver_until_done(service, queue, {"run_id": "run-1", "stage": "brief", "attempt": 1})

    final = runs.get("run-1")
    assert final is not None
    assert final.status is RunStatus.COMPLETED
    assert store.names("run-1") == [f"{stage}.txt" for stage in sorted(STAGES)]
    assert store.get("run-1", "draft.txt") == b"output of draft"
    assert (final.budget.spent, final.budget.reserved) == (len(STAGES) * COST, 0)
    assert len(journal.entries("run-1")) == len(STAGES)
