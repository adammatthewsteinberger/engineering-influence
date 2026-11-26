# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""OutboxDispatchLoop: dispatches on its interval, survives a failed pass, stops when asked, and keeps the secret out of
its logs."""

import asyncio
import logging

import pytest

from engineering_influence.services.interfaces.dispatch_outbox_interface import (
    DispatchOutboxInterface,
)
from engineering_influence.services.outbox_dispatch_loop import OutboxDispatchLoop


class Recording(DispatchOutboxInterface):
    """Counts the passes, and fails the first fail_first of them."""

    def __init__(self, fail_first: int = 0) -> None:
        self.passes: list[bytes] = []
        self._fail_first = fail_first

    async def dispatch(self, secret: bytes) -> int:
        self.passes.append(secret)
        if len(self.passes) <= self._fail_first:
            raise RuntimeError("the receiver is down")
        return 0


def test_passes_repeat_until_the_stop_signal() -> None:
    async def scenario() -> int:
        dispatch = Recording()
        stop = asyncio.Event()
        loop = OutboxDispatchLoop(dispatch, b"k", 0.01)
        task = asyncio.create_task(loop.run(stop))
        await asyncio.sleep(0.05)
        stop.set()
        await task
        return len(dispatch.passes)

    assert asyncio.run(scenario()) >= 2


def test_a_failed_pass_is_logged_and_the_next_one_still_runs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def scenario() -> int:
        dispatch = Recording(fail_first=1)
        stop = asyncio.Event()
        loop = OutboxDispatchLoop(dispatch, b"k", 0.01)
        task = asyncio.create_task(loop.run(stop))
        await asyncio.sleep(0.05)
        stop.set()
        await task
        return len(dispatch.passes)

    with caplog.at_level(logging.ERROR):
        passes = asyncio.run(scenario())
    assert passes >= 2
    assert "webhook dispatch pass failed" in caplog.text


def test_the_secret_is_never_logged(caplog: pytest.LogCaptureFixture) -> None:
    async def scenario() -> None:
        stop = asyncio.Event()
        loop = OutboxDispatchLoop(Recording(fail_first=1), b"topsecret-value", 0.01)
        task = asyncio.create_task(loop.run(stop))
        await asyncio.sleep(0.03)
        stop.set()
        await task

    with caplog.at_level(logging.DEBUG):
        asyncio.run(scenario())
    assert "topsecret-value" not in caplog.text


def test_an_interval_below_the_minimum_is_refused() -> None:
    with pytest.raises(ValueError, match="at least 0.01"):
        OutboxDispatchLoop(Recording(), b"k", 0.0)
