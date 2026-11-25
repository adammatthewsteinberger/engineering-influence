# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Durable event-ledger port."""

from abc import ABC, abstractmethod


class LedgerInterface(ABC):
    """Append-only persistence required by the application layer."""

    __slots__ = ()

    @abstractmethod
    def append(self, event_name: str, payload: dict[str, object]) -> None:
        """Append one event without mutating prior events."""
        raise NotImplementedError
