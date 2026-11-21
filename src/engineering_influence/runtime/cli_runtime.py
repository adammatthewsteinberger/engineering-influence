# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose the command-line application."""

from pathlib import Path
from typing import TYPE_CHECKING

from engineering_influence.controllers.interfaces.run_controller_interface import (
    RunControllerInterface,
)
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interactions.cli.book_cli import BookCli
from engineering_influence.interactions.cli.cli_application import CliApplication
from engineering_influence.interactions.cli.db_cli import DbCli
from engineering_influence.interactions.cli.interfaces.cli_application_interface import (
    CliApplicationInterface,
)
from engineering_influence.interactions.cli.run_cli import RunCli
from engineering_influence.interactions.cli.serve_cli import ServeCli
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.interfaces.schema_migrator_interface import SchemaMigratorInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.runtime.interfaces.cli_runtime_interface import CliRuntimeInterface
from engineering_influence.runtime.interfaces.publishing_controller_factory_interface import (
    PublishingControllerFactoryInterface,
)
from engineering_influence.runtime.serve_starter import ServeStarter
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface
from engineering_influence.services.interfaces.resume_run_interface import ResumeRunInterface
from engineering_influence.services.resume_run import ResumeRun
from engineering_influence.services.start_pipeline import StartPipeline

if TYPE_CHECKING:
    from engineering_influence.controllers.publishing_controller import PublishingController


class CliRuntime(CliRuntimeInterface):
    """Wire ``ei``: a local pipeline planner, the book, server and database commands.

    ``publishing`` replaces the factory that wires the book commands to the real file system and
    toolchain, so a test can drive the whole command line over fakes.
    """

    def __init__(
        self,
        publishing: PublishingControllerFactoryInterface | None = None,
        queue: QueueInterface | None = None,
    ) -> None:
        self._publishing = publishing
        self._queue = queue

    def build(self) -> CliApplicationInterface:
        """Wire the controller, the book commands and the server commands."""
        controller = ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
        return CliApplication(
            controller,
            BookCli(self._publishing_controller),
            ServeCli(ServeStarter()),
            DbCli(self._schema_migrator, self._secret_provider),
            RunCli(self._resume_run, self._cancel_run, self._run_status),
        )

    def _run_repository(self) -> RunRepositoryInterface:
        """Open the stack's run repository, after checking its schema is current."""
        from engineering_influence.repositories.sqlmodel_run_repository import (
            SqlModelRunRepository,
        )

        url = self._secret_provider().require("EI_DATABASE_URL")
        self._schema_migrator().check(url)
        # A one-shot command keeps no pool, so no connection outlives it.
        return SqlModelRunRepository(url, pooled=False)

    def _resume_run(self) -> ResumeRunInterface:
        """Build the resume service; it queues through the broker unless a queue was injected."""
        queue = self._queue
        if queue is None:
            import os

            from engineering_influence.infrastructure.rabbitmq_queue import RabbitMqQueueAdapter

            queue = RabbitMqQueueAdapter(
                self._secret_provider().require("EI_RABBITMQ_URL"),
                os.environ.get("EI_QUEUE_NAME", "engineering-influence.jobs"),
            )
        return ResumeRun(self._run_repository(), queue)

    def _run_status(self) -> RunControllerInterface:
        """Build the read controller; it needs only the database."""
        from engineering_influence.controllers.run_controller import RunController
        from engineering_influence.repositories.sqlmodel_artifact_store import (
            SqlModelArtifactStore,
        )
        from engineering_influence.repositories.sqlmodel_run_repository import (
            SqlModelRunRepository,
        )
        from engineering_influence.services.read_run import ReadRun

        url = self._secret_provider().require("EI_DATABASE_URL")
        self._schema_migrator().check(url)
        return RunController(
            ReadRun(
                SqlModelRunRepository(url, pooled=False),
                SqlModelArtifactStore(url, pooled=False),
            )
        )

    def _cancel_run(self) -> CancelRunInterface:
        """Build the cancel service; it needs only the database."""
        return CancelRun(self._run_repository())

    def _secret_provider(self) -> SecretProviderInterface:
        """Build the secret provider on first use; it needs the ``runtime`` extra."""
        from engineering_influence.infrastructure.security.env_secret_provider import (
            EnvSecretProvider,
        )

        return EnvSecretProvider()

    def _schema_migrator(self) -> SchemaMigratorInterface:
        """Build the migrator on first use; it needs the ``runtime`` extra."""
        from engineering_influence.infrastructure.schema_migrator import SchemaMigrator

        return SchemaMigrator()

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
