"""Job message parsing, delivery settlement, queue topology and the consumer loop."""

import asyncio
import json
import logging
from typing import Any, Self

import aio_pika
import pytest
from pydantic import ValidationError

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.contracts.job_outcome import JobOutcome
from engineering_influence.infrastructure.job_message_handler import JobMessageHandler
from engineering_influence.infrastructure.observability.context_var_correlation import (
    ContextVarCorrelation,
)
from engineering_influence.infrastructure.rabbitmq_job_consumer import RabbitMqJobConsumer
from engineering_influence.infrastructure.rabbitmq_topology import RabbitMqTopology
from engineering_influence.interfaces.alert_port import AlertPort
from engineering_influence.interfaces.metrics_port import MetricsPort
from engineering_influence.services.interfaces.process_job_interface import ProcessJobInterface

TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"


def body(**overrides: Any) -> bytes:
    document = {"job_id": "job-1", "kind": "pipeline.thesis", "payload": {"project_slug": "demo"}}
    return json.dumps({**document, **overrides}).encode()


class Delivery:
    """The parts of an aio-pika incoming message the handler uses."""

    def __init__(self, data: bytes) -> None:
        self.body = data
        self.acked = 0
        self.rejected: list[bool] = []

    async def ack(self) -> None:
        self.acked += 1

    async def reject(self, requeue: bool = False) -> None:
        self.rejected.append(requeue)


class Metrics(MetricsPort):
    def __init__(self) -> None:
        self.seen: dict[str, int] = {}

    def increment(self, name: str, amount: int = 1) -> None:
        self.seen[name] = self.seen.get(name, 0) + amount

    def counters(self) -> dict[str, int]:
        return dict(self.seen)

    def latencies(self) -> dict[str, dict[str, float]]:
        return {}


class Alerts(AlertPort):
    def __init__(self) -> None:
        self.raised: list[tuple[str, str, dict[str, object], str]] = []

    def raise_alert(
        self, severity: str, subject: str, context: dict[str, object], dedup_key: str
    ) -> None:
        self.raised.append((severity, subject, context, dedup_key))


class Processor(ProcessJobInterface):
    def __init__(self, correlation: ContextVarCorrelation, fail: bool = False) -> None:
        self._correlation = correlation
        self._fail = fail
        self.seen: list[tuple[JobMessage, str | None]] = []

    async def process(self, message: JobMessage) -> JobOutcome:
        self.seen.append((message, self._correlation.current()))
        if self._fail:
            raise RuntimeError("database password=hunter2 refused")
        return JobOutcome.COMPLETED


def build(fail: bool = False) -> tuple[JobMessageHandler, Processor, Metrics, Alerts]:
    correlation = ContextVarCorrelation()
    processor, metrics, alerts = Processor(correlation, fail), Metrics(), Alerts()
    return JobMessageHandler(processor, metrics, alerts, correlation), processor, metrics, alerts


def test_a_valid_message_parses() -> None:
    message = JobMessage.parse(body())

    assert (message.job_id, message.kind, message.payload) == (
        "job-1",
        "pipeline.thesis",
        {"project_slug": "demo"},
    )


@pytest.mark.parametrize(
    "data",
    [
        b"not json",
        b"[]",
        b"{}",
        body(job_id=""),
        body(kind=""),
        body(payload="text"),
        body(extra=1),
    ],
)
def test_malformed_messages_do_not_parse(data: bytes) -> None:
    with pytest.raises(ValidationError):
        JobMessage.parse(data)


def test_a_processed_job_is_acknowledged_and_counted() -> None:
    handler, processor, metrics, _ = build()
    delivery = Delivery(body())

    asyncio.run(handler.handle(delivery))

    assert (delivery.acked, delivery.rejected) == (1, [])
    assert metrics.counters() == {"jobs.processed": 1, "jobs.outcome.completed": 1}
    assert processor.seen[0][0].job_id == "job-1"


def test_a_malformed_message_is_dead_lettered_without_being_processed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    handler, processor, metrics, alerts = build()
    delivery = Delivery(b'{"secret": "do-not-log-this-body"}')

    with caplog.at_level(logging.DEBUG):
        asyncio.run(handler.handle(delivery))

    assert (delivery.acked, delivery.rejected) == (0, [False])
    assert metrics.counters() == {"jobs.rejected": 1}
    assert processor.seen == [] and alerts.raised == []
    assert "do-not-log-this-body" not in " ".join(str(vars(r)) for r in caplog.records)


def test_a_failing_job_is_dead_lettered_alerted_and_never_requeued(
    caplog: pytest.LogCaptureFixture,
) -> None:
    handler, _, metrics, alerts = build(fail=True)
    delivery = Delivery(body())

    with caplog.at_level(logging.DEBUG):
        asyncio.run(handler.handle(delivery))

    assert (delivery.acked, delivery.rejected) == (0, [False])
    assert metrics.counters() == {"jobs.failed": 1}
    severity, subject, context, dedup_key = alerts.raised[0]
    assert severity == "error" and dedup_key == "job_failed:job-1"
    assert context == {"job_id": "job-1", "kind": "pipeline.thesis", "error": "RuntimeError"}
    assert "dead-lettered" in subject
    assert "hunter2" not in " ".join(str(vars(r)) for r in caplog.records) + str(alerts.raised)


def test_the_correlation_id_the_job_was_queued_with_is_restored() -> None:
    handler, processor, _, _ = build()

    asyncio.run(handler.handle(Delivery(body(payload={"correlation_id": TRACE}))))

    assert processor.seen[0][1] == TRACE


@pytest.mark.parametrize("payload", [{}, {"correlation_id": 7}])
def test_a_job_without_a_usable_id_still_runs_inside_one(payload: dict[str, Any]) -> None:
    handler, processor, _, _ = build()

    asyncio.run(handler.handle(Delivery(body(payload=payload))))

    assert processor.seen[0][1]


def test_the_topology_declares_a_dead_letter_queue_first() -> None:
    declared: list[tuple[str, dict[str, Any]]] = []

    class Channel:
        async def declare_queue(self, name: str, **options: Any) -> str:
            declared.append((name, options))
            return name

    result = asyncio.run(RabbitMqTopology("jobs").declare(Channel()))

    assert result == "jobs"
    assert declared[0] == ("jobs.dead", {"durable": True})
    assert declared[1][0] == "jobs"
    assert declared[1][1]["durable"] is True
    assert declared[1][1]["arguments"] == {
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": "jobs.dead",
    }


def test_the_topology_needs_a_queue_name() -> None:
    with pytest.raises(ValueError, match="queue name"):
        RabbitMqTopology("  ")
    assert RabbitMqTopology().queue_name == "engineering-influence.jobs"


class FakeQueue:
    def __init__(self) -> None:
        self.callback: Any = None
        self.cancelled: list[str] = []

    async def consume(self, callback: Any) -> str:
        self.callback = callback
        return "tag-1"

    async def cancel(self, tag: str) -> None:
        self.cancelled.append(tag)


class FakeChannel:
    def __init__(self, queue: FakeQueue) -> None:
        self.queue = queue
        self.prefetch = 0
        self.declared: list[str] = []

    async def set_qos(self, prefetch_count: int) -> None:
        self.prefetch = prefetch_count

    async def declare_queue(self, name: str, **options: Any) -> FakeQueue:
        self.declared.append(name)
        return self.queue


class FakeConnection:
    def __init__(self, channel: FakeChannel) -> None:
        self._channel = channel
        self.closed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        self.closed = True

    async def channel(self) -> FakeChannel:
        return self._channel


class Harness:
    def __init__(
        self, handler: Any = None, attempts: int = 30, failures: list[Exception] | None = None
    ) -> None:
        self.queue = FakeQueue()
        self.channel = FakeChannel(self.queue)
        self.connection = FakeConnection(self.channel)
        self.progress = 0
        self.slept: list[float] = []
        self.failures = list(failures or [])
        self.connects = 0
        self.handled: list[Any] = []
        self.handler = handler or self._record

        async def connector(_: str) -> FakeConnection:
            self.connects += 1
            if self.failures:
                raise self.failures.pop(0)
            return self.connection

        async def sleep(seconds: float) -> None:
            self.slept.append(seconds)

        self.consumer = RabbitMqJobConsumer(
            "amqp://broker",
            self,  # type: ignore[arg-type]
            RabbitMqTopology("jobs"),
            on_progress=self._tick,
            connector=connector,
            connect_attempts=attempts,
            retry_seconds=0.5,
            sleep=sleep,
        )

    async def handle(self, message: Any) -> None:
        await self.handler(message)

    async def _record(self, message: Any) -> None:
        self.handled.append(message)

    def _tick(self) -> None:
        self.progress += 1


async def started(harness: Harness) -> tuple[asyncio.Event, asyncio.Task[None]]:
    stop = asyncio.Event()
    task = asyncio.create_task(harness.consumer.run(stop))
    while harness.queue.callback is None and not task.done():
        await asyncio.sleep(0)
    return stop, task


def test_the_consumer_declares_consumes_one_at_a_time_and_reports_progress() -> None:
    async def scenario() -> Harness:
        harness = Harness()
        stop, task = await started(harness)
        await harness.queue.callback("message-1")
        await harness.queue.callback("message-2")
        stop.set()
        await task
        return harness

    harness = asyncio.run(scenario())

    assert harness.channel.prefetch == 1
    assert harness.channel.declared == ["jobs.dead", "jobs"]
    assert harness.handled == ["message-1", "message-2"]
    assert harness.progress == 2
    assert harness.queue.cancelled == ["tag-1"]
    assert harness.connection.closed


def test_stopping_waits_for_the_job_in_flight() -> None:
    order: list[str] = []

    async def scenario() -> None:
        release = asyncio.Event()

        async def slow(_: Any) -> None:
            order.append("started")
            await release.wait()
            order.append("finished")

        harness = Harness(handler=slow)
        stop, task = await started(harness)
        delivery = asyncio.create_task(harness.queue.callback("m"))
        while "started" not in order:
            await asyncio.sleep(0)
        stop.set()
        for _ in range(20):
            await asyncio.sleep(0)
        assert not task.done()  # still draining
        release.set()
        await delivery
        await task
        order.append("closed")

    asyncio.run(scenario())

    assert order == ["started", "finished", "closed"]


def test_a_consumer_without_a_progress_callback_still_works() -> None:
    async def scenario() -> list[Any]:
        harness = Harness()
        harness.consumer._on_progress = None
        stop, task = await started(harness)
        await harness.queue.callback("m")
        stop.set()
        await task
        return harness.handled

    assert asyncio.run(scenario()) == ["m"]


def test_the_consumer_waits_for_a_broker_that_is_still_starting() -> None:
    async def scenario() -> Harness:
        harness = Harness(
            failures=[ConnectionRefusedError(), aio_pika.exceptions.AMQPConnectionError()]
        )
        stop, task = await started(harness)
        stop.set()
        await task
        return harness

    harness = asyncio.run(scenario())

    assert harness.connects == 3
    assert harness.slept == [0.5, 0.5]


def test_the_consumer_gives_up_after_the_last_attempt() -> None:
    async def scenario() -> None:
        harness = Harness(attempts=2, failures=[OSError("a"), OSError("b")])
        await harness.consumer.run(asyncio.Event())

    with pytest.raises(OSError, match="b"):
        asyncio.run(scenario())


def test_at_least_one_connection_attempt_is_required() -> None:
    with pytest.raises(ValueError, match="connect_attempts"):
        RabbitMqJobConsumer("amqp://x", None, RabbitMqTopology(), connect_attempts=0)  # type: ignore[arg-type]
