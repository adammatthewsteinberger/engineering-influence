"""Shared pieces for the integration tests: fakes, a priced executor and a crashable consumer."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika

from engineering_influence.infrastructure.job_message_handler import JobMessageHandler
from engineering_influence.infrastructure.observability.context_var_correlation import (
    ContextVarCorrelation,
)
from engineering_influence.infrastructure.rabbitmq_topology import RabbitMqTopology
from engineering_influence.interfaces.alert_interface import AlertInterface
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.interfaces.metrics_interface import MetricsInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.process_job_interface import ProcessJobInterface

COST = 100


class Metrics(MetricsInterface):
    def __init__(self) -> None:
        self.seen: dict[str, int] = {}

    def increment(self, name: str, amount: int = 1) -> None:
        self.seen[name] = self.seen.get(name, 0) + amount

    def counters(self) -> dict[str, int]:
        return dict(self.seen)

    def latencies(self) -> dict[str, dict[str, float]]:
        return {}


class Alerts(AlertInterface):
    def __init__(self) -> None:
        self.raised: list[str] = []

    def raise_alert(
        self, severity: str, subject: str, context: dict[str, object], dedup_key: str
    ) -> None:
        self.raised.append(subject)


class PricedExecutor(StageExecutorInterface):
    """Journals a fixed cost and stores a deterministic artifact for each stage it runs."""

    def __init__(self, artifacts: ArtifactStoreInterface, journal: JournalInterface) -> None:
        self.artifacts = artifacts
        self.journal = journal
        self.script: list[BaseException] = []
        self.calls: list[tuple[str, int]] = []

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        self.calls.append((run.stage, attempt))
        key = JournalKey("m-1", "p", "v1", run.stage)
        entry = JournalEntry(run.run_id, run.stage, attempt, key, f"text for {run.stage}", COST)
        await asyncio.to_thread(self.journal.record, entry)
        await asyncio.to_thread(
            self.artifacts.put, run.run_id, f"{run.stage}.md", f"output of {run.stage}".encode()
        )
        if self.script:
            raise self.script.pop(0)
        return StageReport()


class Crash(BaseException):
    """The worker process dies here. It is not an Exception, so no handler can swallow it."""


class LostAck:
    """A broker message whose acknowledgement never arrives: the worker died just before it."""

    def __init__(self, message: Any) -> None:
        self._message = message
        self.body = message.body

    async def ack(self) -> None:
        raise Crash

    async def reject(self, requeue: bool = False) -> None:
        raise Crash


def build_handler(router: ProcessJobInterface) -> tuple[JobMessageHandler, Metrics, Alerts]:
    metrics, alerts = Metrics(), Alerts()
    handler = JobMessageHandler(router, metrics, alerts, ContextVarCorrelation())
    return handler, metrics, alerts


async def depth(url: str, name: str) -> int:
    """How many messages are waiting in a queue (unacknowledged ones are not counted)."""
    connection = await aio_pika.connect_robust(url)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(name, passive=True)
        return int(queue.declaration_result.message_count or 0)


async def consume_until(
    url: str,
    topology: RabbitMqTopology,
    handler: JobMessageHandler,
    done: Callable[[], Awaitable[bool]],
    *,
    lose_ack_on: frozenset[int] = frozenset(),
    timeout: float = 60.0,
) -> int:
    """Consume with a fresh connection after every crash until ``done``; return the crash count.

    A crash closes the connection with the message unacknowledged, which is what the death of a
    worker does, so the broker hands the same message to the next connection. Without a crash the
    loop leaves only when no message is being handled, so nothing is left unacknowledged.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    deliveries = 0
    crashes = 0
    active = 0

    def overdue() -> TimeoutError:
        return TimeoutError(f"did not settle within {timeout:.0f}s ({crashes} crashes)")

    while True:
        crashed = asyncio.Event()

        async def on_message(message: Any, crashed: asyncio.Event = crashed) -> None:
            nonlocal deliveries, active
            deliveries += 1
            active += 1
            try:
                lossy = deliveries in lose_ack_on
                await handler.handle(LostAck(message) if lossy else message)
            except Crash:
                crashed.set()
            finally:
                active -= 1

        connection = await aio_pika.connect_robust(url)
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            queue = await topology.declare(channel)
            await queue.consume(on_message)
            while not crashed.is_set() and not (await done() and active == 0):
                if loop.time() > deadline:
                    raise overdue()
                await asyncio.sleep(0.05)
        if crashed.is_set():
            crashes += 1
            continue
        return crashes
