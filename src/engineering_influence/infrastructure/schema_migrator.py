# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs the packaged Alembic migrations."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.schema_migrator_interface import SchemaMigratorInterface


class SchemaMigrator(SchemaMigratorInterface):
    """Drives Alembic without an ini file, from the migrations shipped in the wheel.

    A database problem becomes an ApplicationError that names the failure type and never the
    connection string, which can carry a password.
    """

    def upgrade(self, database_url: str) -> None:
        """Apply every migration the database has not seen."""
        try:
            command.upgrade(self._config(database_url), "head")
        except SQLAlchemyError as error:
            raise self._unavailable(error) from None

    def current(self, database_url: str) -> str | None:
        """The revision the database is at, or None if it was never migrated."""
        try:
            engine = create_engine(database_url)
            try:
                with engine.connect() as connection:
                    return MigrationContext.configure(connection).get_current_revision()
            finally:
                engine.dispose()
        except SQLAlchemyError as error:
            raise self._unavailable(error) from None

    def check(self, database_url: str) -> None:
        """Raise an ApplicationError unless the database is at the latest revision."""
        head = ScriptDirectory.from_config(self._config(database_url)).get_current_head()
        if self.current(database_url) != head:
            raise ApplicationError(
                code="SCHEMA_OUT_OF_DATE",
                message="the database schema is not at the latest revision; run `ei db upgrade`",
                http_status=503,
            )

    def _config(self, database_url: str) -> Config:
        config = Config()
        config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
        config.attributes["database_url"] = database_url
        return config

    def _unavailable(self, error: SQLAlchemyError) -> ApplicationError:
        return ApplicationError(
            code="DATABASE_UNAVAILABLE",
            message=f"cannot reach or migrate the database ({type(error).__name__})",
            http_status=503,
        )
