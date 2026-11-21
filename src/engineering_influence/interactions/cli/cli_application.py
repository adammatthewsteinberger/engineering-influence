# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""CLI interaction over the shared project controller."""

import argparse
import json

from engineering_influence import __version__
from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.controllers.interfaces.project_controller_interface import (
    ProjectControllerInterface,
)
from engineering_influence.interactions.cli.interfaces.book_cli_interface import BookCliInterface
from engineering_influence.interactions.cli.interfaces.cli_application_interface import (
    CliApplicationInterface,
)
from engineering_influence.interactions.cli.interfaces.db_cli_interface import DbCliInterface
from engineering_influence.interactions.cli.interfaces.run_cli_interface import RunCliInterface
from engineering_influence.interactions.cli.interfaces.serve_cli_interface import ServeCliInterface


class CliApplication(CliApplicationInterface):
    """Runs commands without duplicating domain or service behavior.

    Every collaborator is handed in; a composition root in ``runtime`` builds them.
    """

    def __init__(
        self,
        controller: ProjectControllerInterface,
        book_cli: BookCliInterface,
        serve_cli: ServeCliInterface,
        db_cli: DbCliInterface,
        run_cli: RunCliInterface,
    ) -> None:
        self._controller = controller
        self._book_cli = book_cli
        self._serve_cli = serve_cli
        self._db_cli = db_cli
        self._run_cli = run_cli

    def run(self, argv: list[str] | None = None) -> int:
        """Parse the command line and return its process status."""
        parser = argparse.ArgumentParser(prog="ei")
        parser.add_argument(
            "--version", action="version", version=f"engineering-influence {__version__}"
        )
        subparsers = parser.add_subparsers(dest="command")
        pipeline = subparsers.add_parser("pipeline")
        pipeline_subparsers = pipeline.add_subparsers(dest="pipeline_command", required=True)
        start = pipeline_subparsers.add_parser("start")
        start.add_argument("--slug", required=True)
        start.add_argument("--title", required=True)
        start.add_argument("--postulate", action="append", required=True)
        start.add_argument("--stage", action="append")
        self._book_cli.register(subparsers)
        self._serve_cli.register(subparsers)
        self._db_cli.register(subparsers)
        self._run_cli.register(subparsers)
        arguments = parser.parse_args(argv)
        if arguments.command == "book":
            return self._book_cli.run(arguments)
        if arguments.command == "serve":
            return self._serve_cli.run(arguments)
        if arguments.command == "db":
            return self._db_cli.run(arguments)
        if arguments.command == "run":
            return self._run_cli.run(arguments)
        if arguments.command == "pipeline" and arguments.pipeline_command == "start":
            request = ProjectRequest(
                slug=arguments.slug,
                title=arguments.title,
                postulates=tuple(arguments.postulate),
                stages=tuple(arguments.stage or ["thesis"]),
            )
            response = self._controller.start(request)
            print(json.dumps(response.model_dump(), sort_keys=True))
        return 0
