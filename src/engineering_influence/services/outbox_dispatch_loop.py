# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The loop that delivers queued webhook events: one dispatch pass, a wait, and again, until told to stop."""

import asyncio
import logging
from typing import ClassVar

from engineering_influence.services.interfaces.dispatch_outbox_interface import (
    DispatchOutboxInterface,
)
from engineering_influence.services.interfaces.outbox_dispatch_loop_interface import (
    OutboxDispatchLoopInterface,
)

_LOGGER = logging.getLogger(__name__)


class OutboxDispatchLoop(OutboxDispatchLoopInterface):
    """A pass that raises is logged and the loop carries on, so one bad pass never stops delivery for good. The secret is
    passed to the dispatcher and is never logged here."""

    MIN_INTERVAL_SECONDS: ClassVar[float] = 0.01

    def __init__(
        self, dispatch: DispatchOutboxInterface, secret: bytes, interval_seconds: float
    ) -> None:
        if interval_seconds < self.MIN_INTERVAL_SECONDS:
            raise ValueError("the dispatch interval must be at least 0.01 seconds")
        self._dispatch = dispatch
        self._secret = secret
        self._interval = interval_seconds

    async def run(self, stop: asyncio.Event) -> None:
        """Dispatch and wait until the stop signal is set; a stop during a wait ends the loop at once."""
        while not stop.is_set():
            try:
                await self._dispatch.dispatch(self._secret)
            except Exception:  # a failed pass is logged, and the next pass still runs
                _LOGGER.exception("webhook dispatch pass failed")
            try:
                await asyncio.wait_for(stop.wait(), timeout=self._interval)
            except TimeoutError:
                continue
