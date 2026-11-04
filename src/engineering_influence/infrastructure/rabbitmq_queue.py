# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""RabbitMQ queue adapter using aio-pika."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

import aio_pika

from engineering_influence.infrastructure.rabbitmq_topology import RabbitMqTopology
from engineering_influence.interfaces.queue_port import QueuePort


class RabbitMqQueueAdapter(QueuePort):
    """Publish durable jobs through a RabbitMQ default exchange."""

    def __init__(
        self,
        url: str,
        routing_key: str = "engineering-influence.jobs",
        connector: Callable[[str], Awaitable[Any]] = aio_pika.connect_robust,
    ) -> None:
        self._url = url
        self._routing_key = routing_key
        self._connector = connector

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        """Publish one durable job and return its id."""
        job_id = str(uuid4())
        message = {"job_id": job_id, "kind": kind, "payload": payload}
        asyncio.run(self._publish(json.dumps(message, sort_keys=True).encode("utf-8")))
        return job_id

    async def _publish(self, body: bytes) -> None:
        connection = await self._connector(self._url)
        async with connection:
            channel = await connection.channel()
            await RabbitMqTopology(self._routing_key).declare(channel)
            await channel.default_exchange.publish(
                aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                routing_key=self._routing_key,
            )
