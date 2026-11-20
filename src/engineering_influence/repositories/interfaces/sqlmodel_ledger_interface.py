# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SqlModelLedger."""

from abc import ABC, abstractmethod


class SqlModelLedgerInterface(ABC):
    """Persist ledger events through SQLite or PostgreSQL SQLModel engines."""

    __slots__ = ()

    @abstractmethod
    def append(self, event_name: str, payload: dict[str, object]) -> None:
        """Append."""

    @abstractmethod
    def events(self) -> list[tuple[str, dict[str, object]]]:
        """Events."""

    @abstractmethod
    def close(self) -> None:
        """Release the underlying connection pool."""
