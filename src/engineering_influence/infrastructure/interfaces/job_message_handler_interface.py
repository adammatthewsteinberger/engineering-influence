# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for JobMessageHandler."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class JobMessageHandlerInterface(ABC):
    """Acknowledge a processed job; send a malformed or failing one to the dead-letter queue."""

    __slots__ = ()

    @abstractmethod
    async def handle(self, message: Any) -> None:
        """``message`` needs ``body``, ``ack()`` and ``reject(requeue=...)``."""
