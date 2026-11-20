# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SqlModelOutbox."""

from abc import ABC, abstractmethod


class SqlModelOutboxInterface(ABC):
    """Persist idempotent webhook intents with retry metadata."""

    __slots__ = ()

    @abstractmethod
    def enqueue(self, event_id: str, url: str, event_name: str, payload: dict[str, object]) -> None:
        """Enqueue."""

    @abstractmethod
    def pending(self) -> list[tuple[str, str, str, dict[str, object], int]]:
        """Pending."""

    @abstractmethod
    def mark_delivered(self, event_id: str) -> None:
        """Mark delivered."""

    @abstractmethod
    def mark_failed(self, event_id: str) -> int:
        """Mark failed."""

    @abstractmethod
    def mark_dead(self, event_id: str) -> None:
        """Mark dead."""

    @abstractmethod
    def close(self) -> None:
        """Release the underlying connection pool."""
