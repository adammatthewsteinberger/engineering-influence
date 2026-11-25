# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""``ei acp``: the Agent Client Protocol over stdin and stdout. Logs and errors go to stderr, never to stdout."""

import argparse
import sys
from collections.abc import Callable
from typing import TextIO

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.acp.interfaces.application_interface import (
    AcpApplicationInterface,
)
from engineering_influence.interactions.cli.interfaces.acp_cli_interface import AcpCliInterface


class AcpCli(AcpCliInterface):
    """The application is built on first use, because it needs the ``runtime`` extra and the stack's settings.

    The streams are given, not read from ``sys``, so a test serves fake ones and the runtime passes the process's.
    """

    def __init__(
        self,
        application: Callable[[], AcpApplicationInterface],
        reader: TextIO,
        writer: TextIO,
    ) -> None:
        self._application = application
        self._reader = reader
        self._writer = writer

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``acp``."""
        subparsers.add_parser("acp", help="serve the Agent Client Protocol on stdin and stdout")

    def run(self, arguments: argparse.Namespace) -> int:
        """Serve until the input ends and return the process status."""
        del arguments
        try:
            application = self._application()
        except ImportError as error:
            print(
                f"error: acp needs the runtime extra: pip install 'engineering-influence[runtime]' "
                f"({error.name} is missing)",
                file=sys.stderr,
            )
            return 1
        except ApplicationError as error:
            print(f"error: {error.message}", file=sys.stderr)
            return 2
        application.serve(self._reader, self._writer)
        return 0
