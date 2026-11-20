# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Schema migrator port."""

from abc import ABC, abstractmethod


class SchemaMigratorInterface(ABC):
    """Bring a database schema to the revision this release expects, and say whether it is there."""

    __slots__ = ()

    @abstractmethod
    def upgrade(self, database_url: str) -> None:
        """Apply every migration the database has not seen."""

    @abstractmethod
    def current(self, database_url: str) -> str | None:
        """The revision the database is at, or None if it was never migrated."""

    @abstractmethod
    def check(self, database_url: str) -> None:
        """Raise an ApplicationError unless the database is at the latest revision."""
