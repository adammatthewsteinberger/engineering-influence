# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Consume jobs from RabbitMQ one at a time until told to stop."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika

from engineering_influence.infrastructure.job_message_handler import JobMessageHandler
from engineering_influence.infrastructure.rabbitmq_topology import RabbitMqTopology

_LOGGER = logging.getLogger(__name__)


class RabbitMqJobConsumer:
    """Connect (retrying while the broker starts), consume, and finish the job in flight on stop."""

    def __init__(
        self,
        url: str,
        handler: JobMessageHandler,
        topology: RabbitMqTopology,
        on_progress: Callable[[], None] | None = None,
        connector: Callable[[str], Awaitable[Any]] = aio_pika.connect_robust,
        connect_attempts: int = 30,
        retry_seconds: float = 2.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if connect_attempts < 1:
            raise ValueError("connect_attempts must be at least 1")
        self._url = url
        self._handler = handler
        self._topology = topology
        self._on_progress = on_progress
        self._connector = connector
        self._connect_attempts = connect_attempts
        self._retry_seconds = retry_seconds
        self._sleep = sleep
        self._busy = asyncio.Lock()

    async def run(self, stop: asyncio.Event) -> None:
        """Consume until ``stop`` is set, then wait for the job being processed."""
        connection = await self._connect()
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            queue = await self._topology.declare(channel)
            tag = await queue.consume(self._on_message)
            _LOGGER.info("consuming jobs", extra={"queue": self._topology.queue_name})
            await stop.wait()
            await queue.cancel(tag)
            async with self._busy:  # the job in flight finishes before the connection closes
                pass

    async def _connect(self) -> Any:
        attempt = 1
        while True:
            try:
                return await self._connector(self._url)
            except (OSError, aio_pika.exceptions.AMQPException) as error:
                _LOGGER.warning(
                    "broker not reachable yet",
                    extra={"attempt": attempt, "error": type(error).__name__},
                )
                if attempt >= self._connect_attempts:
                    raise
                attempt += 1
                await self._sleep(self._retry_seconds)

    async def _on_message(self, message: Any) -> None:
        async with self._busy:
            await self._handler.handle(message)
            if self._on_progress is not None:
                self._on_progress()
