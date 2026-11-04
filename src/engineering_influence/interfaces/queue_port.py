"""Recoverable queue port."""

from abc import ABC, abstractmethod


class QueuePort(ABC):
    """Queue boundary used by services and implemented by infrastructure."""

    @abstractmethod
    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        """Enqueue one idempotent job and return its identifier."""
        raise NotImplementedError
