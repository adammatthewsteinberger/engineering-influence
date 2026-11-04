"""RabbitMQ adapter contract tests with an injected broker fake."""

import json
from types import TracebackType
from typing import Any, Self

from engineering_influence.infrastructure.rabbitmq_queue import RabbitMqQueueAdapter


class ExchangeFake:
    """Captures published messages."""

    def __init__(self) -> None:
        self.messages: list[tuple[bytes, str]] = []

    async def publish(self, message: Any, routing_key: str) -> None:
        self.messages.append((message.body, routing_key))


class ChannelFake:
    """Provides the default exchange."""

    def __init__(self, exchange: ExchangeFake) -> None:
        self.default_exchange = exchange


class ConnectionFake:
    """Async context-managed broker connection."""

    def __init__(self, channel: ChannelFake) -> None:
        self._channel = channel

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def channel(self) -> ChannelFake:
        return self._channel


def test_rabbitmq_queue_publishes_durable_job() -> None:
    exchange = ExchangeFake()
    connection = ConnectionFake(ChannelFake(exchange))

    async def connector(url: str) -> ConnectionFake:
        assert url == "amqp://broker"
        return connection

    job_id = RabbitMqQueueAdapter("amqp://broker", connector=connector).enqueue(
        "pipeline.thesis", {"project_slug": "demo"}
    )

    body, routing_key = exchange.messages[0]
    assert routing_key == "engineering-influence.jobs"
    assert json.loads(body) == {
        "job_id": job_id,
        "kind": "pipeline.thesis",
        "payload": {"project_slug": "demo"},
    }
