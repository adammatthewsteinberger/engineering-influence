"""A state machine over a book run's whole life: random deliveries, duplicates, failures, resumes.

Hypothesis picks the order of steps and shrinks a failing one to the shortest sequence. After every
step the invariants must hold: a finished run never changes, a run never moves backwards, spend is
exactly the journal's total, artifacts are never rewritten, and a run that is neither finished nor
parked always has a job queued for its current stage, so it can never be stuck.
"""

import asyncio
from collections import deque

from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import FINISHED, BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.resume_run import ResumeRun

STAGES = ("brief", "outline", "draft", "package")
COST = 100
CAP = 1_000_000


class Executor(StageExecutorInterface):
    """Journals a fixed cost and stores a deterministic artifact, then fails as scripted."""

    def __init__(self, journal: InMemoryJournal, store: InMemoryArtifactStore) -> None:
        self.journal = journal
        self.store = store
        self.script: deque[BaseException | None] = deque()

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        key = JournalKey("m-1", "p", "v1", run.stage)
        self.journal.record(JournalEntry(run.run_id, run.stage, attempt, key, run.stage, COST))
        self.store.put(run.run_id, f"{run.stage}.md", f"output of {run.stage}".encode())
        failure = self.script.popleft() if self.script else None
        if failure is not None:
            raise failure
        return StageReport()


class RunLifecycle(RuleBasedStateMachine):
    """One run, one worker at a time, at-least-once delivery."""

    @initialize()
    def start(self) -> None:
        self.runs = InMemoryRunRepository()
        self.journal = InMemoryJournal()
        self.store = InMemoryArtifactStore()
        self.queue = InMemoryQueue()
        self.executor = Executor(self.journal, self.store)
        self.advance = AdvanceRun(
            self.runs, self.journal, self.executor, self.queue, FailureClassifier(), max_attempts=3
        )
        brief = BookBrief(kind=BookKind.NONFICTION, idea="sourdough", budget_micro_usd=CAP)
        plan = StagePlan(kind=BookKind.NONFICTION, stages=STAGES)
        self.runs.save(BookRun("run-1", brief, plan, Budget(cap=CAP)))
        self.queue.enqueue("run.advance", {"run_id": "run-1", "stage": STAGES[0], "attempt": 1})
        self.delivered: list[tuple[str, int]] = []
        self.highest_stage = 0
        self.frozen: BookRun | None = None

    def current(self) -> BookRun:
        run = self.runs.get("run-1")
        assert run is not None
        return run

    def deliver_message(self, stage: str, attempt: int) -> None:
        try:
            asyncio.run(self.advance.advance("run-1", stage, attempt))
        except ApplicationError:
            pass  # a refusal, such as a stage ahead of the run, changes nothing

    @rule(data=st.data())
    def deliver_a_queued_job(self, data: st.DataObject) -> None:
        if not self.queue.jobs:
            return
        index = data.draw(st.integers(0, len(self.queue.jobs) - 1))
        _, payload = self.queue.jobs.pop(index)
        stage, attempt = str(payload["stage"]), int(str(payload["attempt"]))
        self.delivered.append((stage, attempt))
        self.deliver_message(stage, attempt)

    @rule(data=st.data())
    def deliver_an_old_job_again(self, data: st.DataObject) -> None:
        if not self.delivered:
            return
        stage, attempt = data.draw(st.sampled_from(self.delivered))
        self.deliver_message(stage, attempt)

    @rule(
        failure=st.sampled_from(
            [None, TransientStageError("busy"), CapacityExhaustedError("credit"), ValueError("bad")]
        )
    )
    def script_the_next_stage(self, failure: BaseException | None) -> None:
        self.executor.script.append(failure)

    @rule()
    def resume(self) -> None:
        try:
            ResumeRun(self.runs, self.queue).resume("run-1")
        except ApplicationError:
            pass

    @rule()
    def cancel(self) -> None:
        try:
            CancelRun(self.runs).cancel("run-1")
        except ApplicationError:
            pass

    @invariant()
    def a_finished_run_never_changes(self) -> None:
        run = self.current()
        if self.frozen is not None:
            assert run == self.frozen
        elif run.status in FINISHED:
            self.frozen = run

    @invariant()
    def a_run_never_moves_backwards(self) -> None:
        position = STAGES.index(self.current().stage)
        assert position >= self.highest_stage
        self.highest_stage = position

    @invariant()
    def spend_is_exactly_what_the_journal_recorded(self) -> None:
        run = self.current()
        spent = sum(entry.cost_micro_usd for entry in self.journal.entries("run-1"))
        assert (run.budget.spent, run.budget.reserved) == (spent, 0)
        assert run.budget.spent + run.budget.reserved <= run.budget.cap

    @invariant()
    def artifacts_are_the_stages_deterministic_output(self) -> None:
        for name in self.store.names("run-1"):
            stage = name.removesuffix(".md")
            assert stage in STAGES
            assert self.store.get("run-1", name) == f"output of {stage}".encode()

    @invariant()
    def a_completed_run_has_every_artifact(self) -> None:
        run = self.current()
        if run.status is RunStatus.COMPLETED:
            assert run.stage == STAGES[-1]
            assert self.store.names("run-1") == sorted(f"{stage}.md" for stage in STAGES)

    @invariant()
    def a_pending_run_has_not_started(self) -> None:
        if self.current().status is RunStatus.PENDING:
            assert self.current().stage == STAGES[0]
            assert self.journal.entries("run-1") == []

    @invariant()
    def a_run_that_can_still_move_is_never_stuck(self) -> None:
        run = self.current()
        if run.status in FINISHED or run.status is RunStatus.PARKED_CAPACITY:
            return
        waiting = [payload["stage"] for _, payload in self.queue.jobs]
        assert run.stage in waiting, (
            f"{run.status.value} at {run.stage!r} with nothing queued for it"
        )


RunLifecycle.TestCase.settings = settings(
    max_examples=150, stateful_step_count=40, deadline=None, derandomize=True
)
TestRunLifecycle = RunLifecycle.TestCase
