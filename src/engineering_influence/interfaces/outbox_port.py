# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Outbox repository port."""

from abc import ABC, abstractmethod


class OutboxPort(ABC):
    """Store delivery intents until their recipient acknowledges them."""

    @abstractmethod
    def enqueue(
        self,
        event_id: str,
        url: str,
        event_name: str,
        payload: dict[str, object],
    ) -> None:
        """Persist an idempotent delivery intent."""

    @abstractmethod
    def pending(self) -> list[tuple[str, str, str, dict[str, object], int]]:
        """Return undelivered intents in append order."""

    @abstractmethod
    def mark_delivered(self, event_id: str) -> None:
        """Mark one intent as delivered."""
