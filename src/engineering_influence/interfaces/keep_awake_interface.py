# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: keep the computer awake while a block of work runs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class KeepAwakeInterface(ABC):
    """A context in which the machine does not go to sleep, when the platform allows it."""

    __slots__ = ()

    @abstractmethod
    def hold(self) -> AbstractContextManager[None]:
        """A context that keeps the computer awake for its duration and releases it on exit, however it exits."""
