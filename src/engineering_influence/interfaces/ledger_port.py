"""Durable event-ledger port."""

from abc import ABC, abstractmethod


class LedgerPort(ABC):
    """Append-only persistence required by the application layer."""

    @abstractmethod
    def append(self, event_name: str, payload: dict[str, object]) -> None:
        """Append one event without mutating prior events."""
        raise NotImplementedError
