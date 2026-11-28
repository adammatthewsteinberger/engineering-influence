# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Wire the MCP server to the stack's database and queue, and serve it over stdio."""

from collections.abc import Callable
from typing import Any

from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.controllers.run_controller import RunController
from engineering_influence.infrastructure.observability.context_var_correlation import (
    ContextVarCorrelation,
)
from engineering_influence.infrastructure.observability.correlating_queue import CorrelatingQueue
from engineering_influence.infrastructure.observability.json_logging_configurator import (
    JsonLoggingConfigurator,
)
from engineering_influence.infrastructure.observability.process_crash_hooks import (
    ProcessCrashHooks,
)
from engineering_influence.infrastructure.rabbitmq_queue import RabbitMqQueueAdapter
from engineering_influence.infrastructure.schema_migrator import SchemaMigrator
from engineering_influence.interactions.mcp.application import McpApplication
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.interfaces.schema_migrator_interface import SchemaMigratorInterface
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_ledger import SqlModelLedger
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.interfaces.mcp_runtime_interface import McpRuntimeInterface
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.list_runs import ListRuns
from engineering_influence.services.read_run import ReadRun
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.resume_run import ResumeRun
from engineering_influence.services.run_management import RunManagement
from engineering_influence.services.spend_ceiling import SpendCeiling
from engineering_influence.services.start_pipeline import StartPipeline


class McpRuntime(McpRuntimeInterface):
    """The same runs the REST API serves, offered to an MCP host as tools over stdio.

    A stdio server is a child process of the host that started it, so it has no API key: whoever can start the process
    already has the stack's credentials in its environment. Standard output carries the protocol, so logs go to
    standard error only. The server can start, list, resume, cancel and read runs; it grants or denies a run's budget
    requests only when ``mcp_allow_spend`` is set (``EI_MCP_ALLOW_SPEND``), because an agent that could raise its own
    run's cap would have no cap.
    """

    def __init__(
        self,
        settings: AppSettings,
        server: Callable[[Any], None] | None = None,
        queue: QueueInterface | None = None,
        migrator: SchemaMigratorInterface | None = None,
    ) -> None:
        """Remember the settings, server, queue and migrator the MCP host's tools run through."""
        self._settings = settings
        self._server = server
        self._queue = queue
        self._migrator = migrator or SchemaMigrator()
        self._ledger: SqlModelLedger | None = None
        self._stores: list[SqlModelRunRepository | SqlModelArtifactStore] = []

    def build_server(self) -> Any:
        """Wire the ledger, the correlating queue and the run services into an MCP server."""
        correlation = ContextVarCorrelation()
        queue = CorrelatingQueue(
            self._queue
            or RabbitMqQueueAdapter(self._settings.rabbitmq_url, self._settings.queue_name),
            correlation,
        )
        url = self._settings.database_url
        self._migrator.check(url)
        self._ledger = SqlModelLedger(url)
        runs, artifacts = SqlModelRunRepository(url), SqlModelArtifactStore(url)
        self._stores = [runs, artifacts]
        ceiling = SpendCeiling(runs, self._settings.spend_limits)
        manager = RunManagement(
            ListRuns(runs),
            ResumeRun(runs, queue),
            CancelRun(runs),
            ResolveSpendConsent(runs, queue, ceiling),
        )
        return McpApplication(
            ProjectController(StartPipeline(self._ledger, queue)),
            CreateRun(runs, queue, ceiling=ceiling),
            manager,
            RunController(ReadRun(runs, artifacts)),
            allow_spend=self._settings.mcp_allow_spend,
            max_run_budget_micro_usd=self._settings.mcp_max_run_budget_micro_usd,
        ).build()

    def run(self) -> None:
        """Configure logging, build the server, and serve until the host closes the pipe."""
        JsonLoggingConfigurator(self._settings.log_level).configure()
        ProcessCrashHooks().install()
        server = self.build_server()
        try:
            (self._server or self._stdio)(server)
        finally:
            self.close()

    def close(self) -> None:
        """Dispose of every database pool."""
        if self._ledger is not None:
            self._ledger.close()
            self._ledger = None
        for store in self._stores:
            store.close()
        self._stores = []

    @staticmethod
    def _stdio(server: Any) -> None:
        server.run("stdio")
