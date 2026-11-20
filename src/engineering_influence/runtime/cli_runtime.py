# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose the command-line application."""

from pathlib import Path
from typing import TYPE_CHECKING

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
from engineering_influence.runtime.interfaces.publishing_controller_factory_interface import (
    PublishingControllerFactoryInterface,
)
from engineering_influence.runtime.serve_starter import ServeStarter
from engineering_influence.services.start_pipeline import StartPipeline

if TYPE_CHECKING:
    from engineering_influence.controllers.publishing_controller import PublishingController


class CliRuntime(CliRuntimeInterface):
    """Wire ``ei``: a local pipeline planner, the book commands and the server commands.

    ``publishing`` replaces the factory that wires the book commands to the real file system and
    toolchain, so a test can drive the whole command line over fakes.
    """

    def __init__(self, publishing: PublishingControllerFactoryInterface | None = None) -> None:
        self._publishing = publishing

    def build(self) -> CliApplicationInterface:
        """Wire the controller, the book commands and the server commands."""
        controller = ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
        return CliApplication(
            controller, BookCli(self._publishing_controller), ServeCli(ServeStarter())
        )

    def _publishing_controller(self, root: Path) -> "PublishingController":
        """Build the publishing controller on first use.

        The real factory imports Pillow, numpy and the PDF libraries, so it is imported only when
        a book command runs; the rest of ``ei`` keeps working without the ``publishing`` extra.
        """
        factory = self._publishing
        if factory is None:
            from engineering_influence.runtime.publishing_controller_factory import (
                PublishingControllerFactory,
            )

            factory = PublishingControllerFactory()
        return factory.create(root)
