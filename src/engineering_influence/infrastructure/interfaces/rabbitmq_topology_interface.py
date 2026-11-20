# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RabbitMqTopology."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class RabbitMqTopologyInterface(ABC):
    """A durable job queue whose rejected messages go to a dead-letter queue."""

    __slots__ = ()

    @abstractmethod
    async def declare(self, channel: Any) -> Any:
        """Declare both queues (idempotent) and return the job queue."""
