# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RabbitMqJobConsumer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio


class RabbitMqJobConsumerInterface(ABC):
    """Connect (retrying while the broker starts), consume, and finish the job in flight on stop."""

    __slots__ = ()

    @abstractmethod
    async def run(self, stop: asyncio.Event) -> None:
        """Consume until ``stop`` is set, then wait for the job being processed."""
