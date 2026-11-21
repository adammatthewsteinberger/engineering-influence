"""Jobs through a real RabbitMQ: publishing, consuming, dead-lettering and redelivery."""

import asyncio
from typing import Any

import aio_pika
import pytest
from rig import Crash, build_handler, depth

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.contracts.job_outcome import JobOutcome
from engineering_influence.infrastructure.rabbitmq_job_consumer import RabbitMqJobConsumer
from engineering_influence.infrastructure.rabbitmq_queue import RabbitMqQueueAdapter
from engineering_influence.infrastructure.rabbitmq_topology import RabbitMqTopology
from engineering_influence.services.interfaces.process_job_interface import ProcessJobInterface

pytestmark = pytest.mark.integration


class Processor(ProcessJobInterface):
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.seen: list[JobMessage] = []

    async def process(self, message: JobMessage) -> JobOutcome:
        self.seen.append(message)
        if self.failure is not None:
            raise self.failure
        return JobOutcome.COMPLETED


async def until(condition: Any, seconds: float = 15.0) -> None:
    deadline = asyncio.get_running_loop().time() + seconds
    while not await condition():
        if asyncio.get_running_loop().time() > deadline:
            raise TimeoutError("condition not met in time")
        await asyncio.sleep(0.05)


async def publish_raw(url: str, topology: RabbitMqTopology, body: bytes) -> None:
    connection = await aio_pika.connect_robust(url)
    async with connection:
        channel = await connection.channel()
        await topology.declare(channel)
        await channel.default_exchange.publish(
            aio_pika.Message(body=body), routing_key=topology.queue_name
        )


async def with_consumer(
    url: str, topology: RabbitMqTopology, processor: Processor, scenario: Any
) -> Any:
    handler, metrics, alerts = build_handler(processor)
    consumer = RabbitMqJobConsumer(url, handler, topology)
    stop = asyncio.Event()
    task = asyncio.create_task(consumer.run(stop))
    try:
        return await scenario(metrics, alerts)
    finally:
        stop.set()
        await task


def test_a_published_job_is_consumed_and_acknowledged(rabbitmq_url: str, queue_name: str) -> None:
    topology = RabbitMqTopology(queue_name)
    processor = Processor()
    adapter = RabbitMqQueueAdapter(rabbitmq_url, queue_name)

    async def scenario(metrics: Any, alerts: Any) -> None:
        job_id = await asyncio.to_thread(
            adapter.enqueue, "pipeline.thesis", {"project_slug": "demo"}
        )
        await until(lambda: _seen(processor, 1))
        message = processor.seen[0]
        assert (message.job_id, message.kind, message.schema_version) == (
            job_id,
            "pipeline.thesis",
            1,
        )
        assert message.payload == {"project_slug": "demo"}
        await until(lambda: _empty(rabbitmq_url, queue_name))
        assert metrics.seen["jobs.processed"] == 1

    asyncio.run(with_consumer(rabbitmq_url, topology, processor, scenario))
    assert asyncio.run(depth(rabbitmq_url, topology.dead_queue_name)) == 0


async def _seen(processor: Processor, count: int) -> bool:
    return len(processor.seen) >= count


async def _empty(url: str, name: str) -> bool:
    return await depth(url, name) == 0


def test_a_job_published_before_any_consumer_exists_is_kept(
    rabbitmq_url: str, queue_name: str
) -> None:
    RabbitMqQueueAdapter(rabbitmq_url, queue_name).enqueue(
        "pipeline.thesis", {"project_slug": "demo"}
    )
    assert asyncio.run(depth(rabbitmq_url, queue_name)) == 1


def test_a_published_job_is_persistent(rabbitmq_url: str, queue_name: str) -> None:
    RabbitMqQueueAdapter(rabbitmq_url, queue_name).enqueue(
        "pipeline.thesis", {"project_slug": "demo"}
    )

    async def fetch() -> aio_pika.DeliveryMode:
        connection = await aio_pika.connect_robust(rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            queue = await RabbitMqTopology(queue_name).declare(channel)
            message = await queue.get(timeout=10)
            await message.reject(requeue=False)
            return message.delivery_mode

    assert asyncio.run(fetch()) is aio_pika.DeliveryMode.PERSISTENT


def test_a_malformed_message_goes_to_the_dead_letter_queue(
    rabbitmq_url: str, queue_name: str
) -> None:
    topology = RabbitMqTopology(queue_name)
    processor = Processor()

    async def scenario(metrics: Any, alerts: Any) -> None:
        await publish_raw(rabbitmq_url, topology, b"not json at all")
        await until(lambda: _has(rabbitmq_url, topology.dead_queue_name, 1))
        assert metrics.seen["jobs.rejected"] == 1

    asyncio.run(with_consumer(rabbitmq_url, topology, processor, scenario))
    assert processor.seen == []
    assert asyncio.run(depth(rabbitmq_url, queue_name)) == 0


async def _has(url: str, name: str, count: int) -> bool:
    return await depth(url, name) == count


def test_a_failing_job_is_dead_lettered_once_with_an_alert(
    rabbitmq_url: str, queue_name: str
) -> None:
    topology = RabbitMqTopology(queue_name)
    processor = Processor(RuntimeError("database password=hunter2 refused"))
    adapter = RabbitMqQueueAdapter(rabbitmq_url, queue_name)

    async def scenario(metrics: Any, alerts: Any) -> None:
        await asyncio.to_thread(adapter.enqueue, "pipeline.thesis", {"project_slug": "demo"})
        await until(lambda: _has(rabbitmq_url, topology.dead_queue_name, 1))
        assert alerts.raised == ["job pipeline.thesis failed and was dead-lettered"]
        assert "hunter2" not in " ".join(alerts.raised)

    asyncio.run(with_consumer(rabbitmq_url, topology, processor, scenario))
    assert len(processor.seen) == 1
    assert asyncio.run(depth(rabbitmq_url, queue_name)) == 0


def test_a_message_left_unacknowledged_by_a_dead_worker_is_redelivered(
    rabbitmq_url: str, queue_name: str
) -> None:
    topology = RabbitMqTopology(queue_name)
    RabbitMqQueueAdapter(rabbitmq_url, queue_name).enqueue("run.advance", {"run_id": "run-1"})

    async def scenario() -> tuple[bool, bool]:
        received: list[Any] = []
        first = await aio_pika.connect_robust(rabbitmq_url)
        async with first:
            channel = await first.channel()
            queue = await topology.declare(channel)

            async def take(message: Any) -> None:
                received.append(message.redelivered)
                raise Crash  # never acknowledged: the worker "dies" holding the message

            await queue.consume(take)
            await until(lambda: _count(received, 1))
        # leaving the block closed the connection with the message unacknowledged
        second = await aio_pika.connect_robust(rabbitmq_url)
        async with second:
            channel = await second.channel()
            queue = await topology.declare(channel)
            message = await queue.get(timeout=10)
            redelivered = bool(message.redelivered)
            await message.ack()
        return received[0], redelivered

    first_time, second_time = asyncio.run(scenario())
    assert (first_time, second_time) == (False, True)
    assert asyncio.run(depth(rabbitmq_url, queue_name)) == 0


async def _count(items: list[Any], count: int) -> bool:
    return len(items) >= count
