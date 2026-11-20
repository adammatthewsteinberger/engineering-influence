# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for WorkerRuntime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio

    from engineering_influence.infrastructure.observability.worker_heartbeat import WorkerHeartbeat
    from engineering_influence.infrastructure.rabbitmq_job_consumer import RabbitMqJobConsumer


class WorkerRuntimeInterface(ABC):
    """Build the worker from settings and consume until a stop signal."""

    __slots__ = ()

    @abstractmethod
    def build(self) -> tuple[RabbitMqJobConsumer, WorkerHeartbeat]:
        """Wire the consumer and the heartbeat that watches it."""

    @abstractmethod
    async def serve(self, stop: asyncio.Event) -> None:
        """Run until ``stop`` is set; the heartbeat always stops with the consumer."""

    @abstractmethod
    def close(self) -> None:
        """Dispose of the database pool."""

    @abstractmethod
    def run(self) -> None:
        """Configure the process and serve until SIGINT or SIGTERM."""
