# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for OutboxDispatchLoop."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod


class OutboxDispatchLoopInterface(ABC):
    """Delivers queued webhook events on an interval until it is asked to stop."""

    __slots__ = ()

    @abstractmethod
    async def run(self, stop: asyncio.Event) -> None:
        """Dispatch, wait for the interval or the stop signal, and repeat until the stop signal is set."""
