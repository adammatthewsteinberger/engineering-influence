# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose the command-line application."""

from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interactions.cli.book_cli import BookCli
from engineering_influence.interactions.cli.cli_application import CliApplication
from engineering_influence.interactions.cli.interfaces.cli_application_interface import (
    CliApplicationInterface,
)
from engineering_influence.interactions.cli.serve_cli import ServeCli
from engineering_influence.runtime.interfaces.cli_runtime_interface import CliRuntimeInterface
from engineering_influence.runtime.serve_starter import ServeStarter
from engineering_influence.services.start_pipeline import StartPipeline


class CliRuntime(CliRuntimeInterface):
    """Wire ``ei``: a local pipeline planner, the book commands and the server commands."""

    def build(self) -> CliApplicationInterface:
        """Wire the controller, the book commands and the server commands."""
        controller = ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
        return CliApplication(controller, BookCli(), ServeCli(ServeStarter()))
