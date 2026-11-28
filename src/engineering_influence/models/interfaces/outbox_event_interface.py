# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for OutboxEvent."""

from __future__ import annotations

from abc import ABC, abstractmethod


class OutboxEventInterface(ABC):
    """A webhook event waiting to be delivered, written in the same commit as the change it describes."""

    __slots__ = ()

    @abstractmethod
    def record_key(self) -> str:
        """The id that makes the event unique: the same event is never queued twice."""
