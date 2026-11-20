# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``db`` command group: bring the database schema up to date."""

import argparse
import sys
from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.db_cli_interface import DbCliInterface
from engineering_influence.interfaces.schema_migrator_interface import SchemaMigratorInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface


class DbCli(DbCliInterface):
    """Run the migrations against ``EI_DATABASE_URL`` and report the revision reached.

    The migrator and the secret provider are built on first use, because both need the ``runtime``
    extra; a missing extra
    or a configuration problem prints one line and exits non-zero, never a traceback that could
    carry a connection string.
    """

    def __init__(
        self,
        migrator: Callable[[], SchemaMigratorInterface],
        secrets: Callable[[], SecretProviderInterface],
    ) -> None:
        self._migrator = migrator
        self._secrets = secrets

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``db upgrade``."""
        db = subparsers.add_parser("db", help="manage the database schema")
        commands = db.add_subparsers(dest="db_command", required=True)
        commands.add_parser("upgrade", help="bring the schema to the latest revision")

    def run(self, arguments: argparse.Namespace) -> int:
        """Upgrade the schema; return the process status."""
        try:
            url = self._secrets().require("EI_DATABASE_URL")
            migrator = self._migrator()
            migrator.upgrade(url)
            revision = migrator.current(url)
        except ImportError as error:
            print(
                "error: db needs the runtime extra: "
                f"pip install 'engineering-influence[runtime]' ({error.name} is missing)",
                file=sys.stderr,
            )
            return 1
        except ApplicationError as error:
            print(f"error: {error.message}", file=sys.stderr)
            return 2
        print(f"database schema is at revision {revision}")
        return 0
