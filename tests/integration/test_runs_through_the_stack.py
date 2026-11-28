"""A book run through real PostgreSQL and RabbitMQ, with workers that die at the worst moments.

A "death" closes the broker connection with the message unacknowledged, exactly as a killed
process does, so the broker redelivers it. The run must still finish with every artifact present
and byte-identical, the spend exactly the sum of the journal, and nothing in the dead-letter queue.
"""

import asyncio
from dataclasses import dataclass

import pytest
from rig import COST, Crash, PricedExecutor, build_handler, consume_until, depth

from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.infrastructure.job_message_handler import JobMessageHandler
from engineering_influence.infrastructure.rabbitmq_queue import RabbitMqQueueAdapter
from engineering_influence.infrastructure.rabbitmq_topology import RabbitMqTopology
from engineering_influence.infrastructure.schema_migrator import SchemaMigrator
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.outbox_event import OutboxEvent
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_journal import SqlModelJournal
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.job_router import JobRouter
from engineering_influence.services.process_run_job import ProcessRunJob
from engineering_influence.services.resume_run import ResumeRun

pytestmark = pytest.mark.integration

STAGES = ("brief", "outline", "draft", "package")
CAP = 5_000_000


class ChaosRuns(SqlModelRunRepository):
    """Dies instead of storing its nth change to a run."""

    def __init__(self, url: str, crash_on: int) -> None:
        super().__init__(url)
        self.crash_on = crash_on
        self.writes = 0

    def swap_with_events(
        self, expected: BookRun, replacement: BookRun, events: tuple[OutboxEvent, ...]
    ) -> bool:
        # AdvanceRun stores every change through swap_with_events, so the crash is injected there.
        self.writes += 1
        if self.writes == self.crash_on:
            raise Crash
        return super().swap_with_events(expected, replacement, events)


class ChaosQueue(RabbitMqQueueAdapter):
    """Dies instead of publishing its nth job."""

    def __init__(self, url: str, name: str, crash_on: int) -> None:
        super().__init__(url, name)
        self.crash_on = crash_on
        self.publishes = 0

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        self.publishes += 1
        if self.publishes == self.crash_on:
            raise Crash
        return super().enqueue(kind, payload)


@dataclass
class Stack:
    url: str
    topology: RabbitMqTopology
    runs: ChaosRuns
    journal: SqlModelJournal
    artifacts: SqlModelArtifactStore
    executor: PricedExecutor
    queue: ChaosQueue
    handler: JobMessageHandler
    alerts: object

    async def status(self) -> RunStatus | None:
        run = await asyncio.to_thread(self.runs.get, "run-1")
        return None if run is None else run.status

    async def finished(self) -> bool:
        return await self.status() is RunStatus.COMPLETED

    async def settled(self) -> bool:
        return await depth(self.url, self.topology.queue_name) == 0

    def close(self) -> None:
        for store in (self.runs, self.journal, self.artifacts):
            store.close()


def build(
    postgres_url: str, rabbitmq_url: str, queue_name: str, crash_write: int, crash_enqueue: int
) -> Stack:
    SchemaMigrator().upgrade(postgres_url)
    runs = ChaosRuns(postgres_url, crash_write)
    journal, artifacts = SqlModelJournal(postgres_url), SqlModelArtifactStore(postgres_url)
    queue = ChaosQueue(rabbitmq_url, queue_name, crash_enqueue)
    executor = PricedExecutor(artifacts, journal)
    advance = AdvanceRun(runs, journal, executor, queue, FailureClassifier())
    handler, _, alerts = build_handler(JobRouter({"run": ProcessRunJob(advance)}))
    brief = BookBrief(kind=BookKind.NONFICTION, idea="sourdough", budget_micro_usd=CAP)
    plan = StagePlan(kind=BookKind.NONFICTION, stages=STAGES)
    SqlModelRunRepository.save(runs, BookRun("run-1", brief, plan, Budget(cap=CAP)))
    return Stack(
        rabbitmq_url,
        RabbitMqTopology(queue_name),
        runs,
        journal,
        artifacts,
        executor,
        queue,
        handler,
        alerts,
    )


async def start(stack: Stack) -> None:
    first = RabbitMqQueueAdapter(stack.url, stack.topology.queue_name)
    await asyncio.to_thread(
        first.enqueue, "run.advance", {"run_id": "run-1", "stage": STAGES[0], "attempt": 1}
    )


async def verify_finished_cleanly(stack: Stack) -> None:
    run = await asyncio.to_thread(stack.runs.get, "run-1")
    assert run is not None
    assert run.status is RunStatus.COMPLETED
    assert (run.budget.spent, run.budget.reserved) == (len(STAGES) * COST, 0)
    names = await asyncio.to_thread(stack.artifacts.names, "run-1")
    assert names == sorted(f"{stage}.md" for stage in STAGES)
    for stage in STAGES:
        assert await asyncio.to_thread(stack.artifacts.get, "run-1", f"{stage}.md") == (
            f"output of {stage}".encode()
        )
    assert len(await asyncio.to_thread(stack.journal.entries, "run-1")) == len(STAGES)
    assert await depth(stack.url, stack.topology.dead_queue_name) == 0
    assert stack.alerts.raised == []  # type: ignore[attr-defined]


SCENARIOS = [
    pytest.param(0, 0, frozenset(), 0, id="nothing goes wrong"),
    pytest.param(2, 0, frozenset(), 1, id="the second change to the run is lost"),
    pytest.param(4, 0, frozenset(), 1, id="the last change to the run is lost"),
    pytest.param(0, 1, frozenset(), 1, id="the first next-stage job is never published"),
    pytest.param(0, 3, frozenset(), 1, id="the last next-stage job is never published"),
    pytest.param(3, 2, frozenset(), 2, id="a lost change and a lost job"),
    pytest.param(0, 0, frozenset({1, 3}), 2, id="the worker dies before acknowledging twice"),
]


@pytest.mark.parametrize(("crash_write", "crash_enqueue", "lose_ack", "crashes"), SCENARIOS)
def test_a_run_finishes_exactly_once_however_the_workers_die(
    postgres_url: str,
    rabbitmq_url: str,
    queue_name: str,
    crash_write: int,
    crash_enqueue: int,
    lose_ack: frozenset[int],
    crashes: int,
) -> None:
    stack = build(postgres_url, rabbitmq_url, queue_name, crash_write, crash_enqueue)

    async def scenario() -> int:
        await start(stack)
        died = await consume_until(
            rabbitmq_url, stack.topology, stack.handler, stack.finished, lose_ack_on=lose_ack
        )
        # Duplicates left behind by the deaths must now drain without changing anything.
        before = await asyncio.to_thread(stack.runs.get, "run-1")
        await consume_until(rabbitmq_url, stack.topology, stack.handler, stack.settled)
        assert await asyncio.to_thread(stack.runs.get, "run-1") == before
        await verify_finished_cleanly(stack)
        return died

    try:
        assert asyncio.run(scenario()) == crashes
    finally:
        stack.close()


def test_a_run_parked_for_credit_is_resumed_through_the_real_broker(
    postgres_url: str, rabbitmq_url: str, queue_name: str
) -> None:
    stack = build(postgres_url, rabbitmq_url, queue_name, 0, 0)
    stack.executor.script = [CapacityExhaustedError("credit exhausted")]

    async def parked() -> bool:
        return await stack.status() is RunStatus.PARKED_CAPACITY

    async def scenario() -> None:
        await start(stack)
        await consume_until(rabbitmq_url, stack.topology, stack.handler, parked)
        await consume_until(rabbitmq_url, stack.topology, stack.handler, stack.settled)
        assert await stack.status() is RunStatus.PARKED_CAPACITY

        resumed = await asyncio.to_thread(
            ResumeRun(stack.runs, RabbitMqQueueAdapter(rabbitmq_url, queue_name)).resume, "run-1"
        )
        assert resumed.status is RunStatus.RUNNING
        await consume_until(rabbitmq_url, stack.topology, stack.handler, stack.finished)
        await consume_until(rabbitmq_url, stack.topology, stack.handler, stack.settled)
        await verify_finished_cleanly(stack)

    try:
        asyncio.run(scenario())
    finally:
        stack.close()
