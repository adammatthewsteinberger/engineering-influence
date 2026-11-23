# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose and run the job worker."""

import asyncio
import logging
import os
import signal
from datetime import date

from engineering_influence.infrastructure.deterministic_runner import DeterministicRunner
from engineering_influence.infrastructure.job_message_handler import JobMessageHandler
from engineering_influence.infrastructure.non_empty_artifact_gate import NonEmptyArtifactGate
from engineering_influence.infrastructure.observability.bootstrap_alert_dispatcher import (
    BootstrapAlertDispatcher,
)
from engineering_influence.infrastructure.observability.bootstrap_metrics import BootstrapMetrics
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
from engineering_influence.infrastructure.observability.traced_run_phase import TracedRunPhase
from engineering_influence.infrastructure.observability.worker_heartbeat import WorkerHeartbeat
from engineering_influence.infrastructure.rabbitmq_job_consumer import RabbitMqJobConsumer
from engineering_influence.infrastructure.rabbitmq_queue import RabbitMqQueueAdapter
from engineering_influence.infrastructure.rabbitmq_topology import RabbitMqTopology
from engineering_influence.infrastructure.schema_migrator import SchemaMigrator
from engineering_influence.infrastructure.security.env_secret_provider import EnvSecretProvider
from engineering_influence.interfaces.schema_migrator_interface import SchemaMigratorInterface
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_journal import SqlModelJournal
from engineering_influence.repositories.sqlmodel_ledger import SqlModelLedger
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.interfaces.stage_executor_runtime_interface import (
    StageExecutorRuntimeInterface,
)
from engineering_influence.runtime.interfaces.worker_runtime_interface import WorkerRuntimeInterface
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.job_router import JobRouter
from engineering_influence.services.process_job import ProcessJob
from engineering_influence.services.process_run_job import ProcessRunJob
from engineering_influence.services.run_phase import RunPhase

_LOGGER = logging.getLogger(__name__)


class WorkerRuntime(WorkerRuntimeInterface):
    """Build the worker from settings and consume until a stop signal.

    The pipeline runner and gate are deterministic placeholders. A run's stages are done by the
    free local model unless ``EI_STAGE_EXECUTOR`` says ``model`` (your own) or ``deterministic`` (the offline placeholder); see ``StageExecutorRuntime``.
    """

    def __init__(
        self,
        settings: AppSettings,
        migrator: SchemaMigratorInterface | None = None,
        executors: StageExecutorRuntimeInterface | None = None,
    ) -> None:
        self._settings = settings
        self._migrator = migrator or SchemaMigrator()
        self._executors = executors or StageExecutorRuntime(
            os.environ, EnvSecretProvider(), date.today()
        )
        self._ledger: SqlModelLedger | None = None
        self._stores: list[SqlModelRunRepository | SqlModelJournal | SqlModelArtifactStore] = []

    def build(self) -> tuple[RabbitMqJobConsumer, WorkerHeartbeat]:
        """Wire the consumer and the heartbeat that watches it."""
        metrics = BootstrapMetrics()
        alerts = BootstrapAlertDispatcher()
        correlation = ContextVarCorrelation()
        topology = RabbitMqTopology(self._settings.queue_name)
        queue = CorrelatingQueue(
            RabbitMqQueueAdapter(self._settings.rabbitmq_url, self._settings.queue_name),
            correlation,
        )
        self._migrator.check(self._settings.database_url)
        url = self._settings.database_url
        self._ledger = SqlModelLedger(url)
        runs, journal, artifacts = (
            SqlModelRunRepository(url),
            SqlModelJournal(url),
            SqlModelArtifactStore(url),
        )
        self._stores = [runs, journal, artifacts]
        advance = AdvanceRun(
            runs,
            journal,
            self._executors.build(artifacts, journal),
            queue,
            FailureClassifier(),
        )
        process_job = JobRouter(
            {
                "pipeline": ProcessJob(
                    TracedRunPhase(RunPhase(DeterministicRunner(), NonEmptyArtifactGate())),
                    self._ledger,
                    queue,
                ),
                "run": ProcessRunJob(advance),
            }
        )
        heartbeat = WorkerHeartbeat(metrics, alerts)
        consumer = RabbitMqJobConsumer(
            self._settings.rabbitmq_url,
            JobMessageHandler(process_job, metrics, alerts, correlation),
            topology,
            on_progress=heartbeat.record_progress,
        )
        return consumer, heartbeat

    async def serve(self, stop: asyncio.Event) -> None:
        """Run until ``stop`` is set; the heartbeat always stops with the consumer."""
        consumer, heartbeat = self.build()
        heartbeat.start()
        try:
            await consumer.run(stop)
        finally:
            heartbeat.stop()
            self.close()

    def close(self) -> None:
        """Dispose of every database pool."""
        if self._ledger is not None:
            self._ledger.close()
            self._ledger = None
        for store in self._stores:
            store.close()
        self._stores = []
        self._executors.close()

    def run(self) -> None:
        """Configure the process and serve until SIGINT or SIGTERM."""
        JsonLoggingConfigurator(self._settings.log_level).configure()
        ProcessCrashHooks().install()
        asyncio.run(self._main())

    async def _main(self) -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for number in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(number, stop.set)
        _LOGGER.info("worker starting")
        await self.serve(stop)
        _LOGGER.info("worker stopped")
