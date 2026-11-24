# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``serve`` command group: run the API, the worker or the MCP server."""

import argparse
import sys

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.serve_cli_interface import ServeCliInterface
from engineering_influence.interfaces.serve_starter_interface import ServeStarterInterface


class ServeCli(ServeCliInterface):
    """Start a long-running process and turn a failure into an exit status.

    A configuration problem prints which variable is wrong and exits 2. It never prints a
    traceback, which could carry a connection string.
    """

    def __init__(self, starter: ServeStarterInterface) -> None:
        self._starter = starter

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``serve api``, ``serve worker`` and ``serve mcp``."""
        serve = subparsers.add_parser("serve", help="run the API, the worker or the MCP server")
        serve.add_argument("target", choices=("api", "worker", "mcp"))

    def run(self, arguments: argparse.Namespace) -> int:
        """Start the chosen process; return its exit status."""
        try:
            self._starter.start(arguments.target)
        except ImportError as error:
            extras = "mcp,runtime" if arguments.target == "mcp" else "api,runtime"
            print(
                f"error: serve {arguments.target} needs the {extras.replace(',', ' and ')} extras: "
                f"pip install 'engineering-influence[{extras}]' ({error.name} is missing)",
                file=sys.stderr,
            )
            return 1
        except (ApplicationError, ValueError) as error:
            message = error.message if isinstance(error, ApplicationError) else str(error)
            print(f"error: {message}", file=sys.stderr)
            return 2
        return 0
