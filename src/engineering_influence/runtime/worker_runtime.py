# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose and run the job worker."""

import asyncio
import logging
import os
import signal
import time
from datetime import date

import httpx

from engineering_influence.infrastructure.deterministic_runner import DeterministicRunner
from engineering_influence.infrastructure.job_message_handler import JobMessageHandler
from engineering_influence.infrastructure.non_empty_artifact_gate import NonEmptyArtifactGate
from engineering_influence.infrastructure.object_storage.s3_artifact_store import S3ArtifactStore
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
from engineering_influence.infrastructure.observability.otel_tracing import OtelTracing
from engineering_influence.infrastructure.observability.process_crash_hooks import (
    ProcessCrashHooks,
)
from engineering_influence.infrastructure.observability.traced_dispatch_outbox import (
    TracedDispatchOutbox,
)
from engineering_influence.infrastructure.observability.traced_run_phase import TracedRunPhase
from engineering_influence.infrastructure.observability.worker_heartbeat import WorkerHeartbeat
from engineering_influence.infrastructure.rabbitmq_job_consumer import RabbitMqJobConsumer
from engineering_influence.infrastructure.rabbitmq_queue import RabbitMqQueueAdapter
from engineering_influence.infrastructure.rabbitmq_topology import RabbitMqTopology
from engineering_influence.infrastructure.schema_migrator import SchemaMigrator
from engineering_influence.infrastructure.security.env_secret_provider import EnvSecretProvider
from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)
from engineering_influence.infrastructure.webhooks.delivery import WebhookDelivery
from engineering_influence.interfaces.schema_migrator_interface import SchemaMigratorInterface
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_journal import SqlModelJournal
from engineering_influence.repositories.sqlmodel_ledger import SqlModelLedger
from engineering_influence.repositories.sqlmodel_outbox import SqlModelOutbox
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.artifact_store_factory import ArtifactStoreFactory
from engineering_influence.runtime.interfaces.stage_executor_runtime_interface import (
    StageExecutorRuntimeInterface,
)
from engineering_influence.runtime.interfaces.worker_runtime_interface import WorkerRuntimeInterface
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.dispatch_outbox import DispatchOutbox
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.job_router import JobRouter
from engineering_influence.services.outbox_dispatch_loop import OutboxDispatchLoop
from engineering_influence.services.process_job import ProcessJob
from engineering_influence.services.process_run_job import ProcessRunJob
from engineering_influence.services.run_event_builder import RunEventBuilder
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
        """Remember the settings, migrator and stage executors the worker runs with."""
        self._settings = settings
        self._migrator = migrator or SchemaMigrator()
        self._executors = executors or StageExecutorRuntime(
            os.environ, EnvSecretProvider(), date.today()
        )
        self._ledger: SqlModelLedger | None = None
        self._stores: list[
            SqlModelRunRepository | SqlModelJournal | SqlModelArtifactStore | S3ArtifactStore
        ] = []
        self._dispatch: OutboxDispatchLoop | None = None
        self._http: httpx.AsyncClient | None = None

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
            ArtifactStoreFactory().build(self._settings),
        )
        self._stores = [runs, journal, artifacts]
        advance = AdvanceRun(
            runs,
            journal,
            self._executors.build(artifacts, journal),
            queue,
            FailureClassifier(),
            events=RunEventBuilder(self._settings.webhook_urls),
        )
        self._dispatch = self.webhook_dispatch(metrics, alerts)
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

    def webhook_dispatch(
        self, metrics: BootstrapMetrics, alerts: BootstrapAlertDispatcher
    ) -> OutboxDispatchLoop | None:
        """The loop that delivers the run's webhook events, or None when no receiver is configured.

        The signing secret goes only to the dispatcher, and the traced wrapper records it as sensitive.
        """
        if not self._settings.webhook_urls:
            return None
        self._http = httpx.AsyncClient(timeout=10.0)
        delivery = WebhookDelivery(self._http, PublicHttpsUrlPolicy(), time.time)
        dispatch = DispatchOutbox(
            SqlModelOutbox(self._settings.database_url), delivery, metrics, alerts
        )
        return OutboxDispatchLoop(
            TracedDispatchOutbox(dispatch),
            self._settings.webhook_secret.encode("utf-8"),
            self._settings.webhook_interval_seconds,
        )

    async def serve(self, stop: asyncio.Event) -> None:
        """Run until ``stop`` is set: the consumer and, when a receiver is configured, the webhook dispatch loop."""
        consumer, heartbeat = self.build()
        await self.gather(consumer, heartbeat, self._dispatch, stop)

    async def gather(
        self,
        consumer: RabbitMqJobConsumer,
        heartbeat: WorkerHeartbeat,
        dispatch: OutboxDispatchLoop | None,
        stop: asyncio.Event,
    ) -> None:
        """Run the consumer and the dispatch loop until ``stop`` is set. The heartbeat always stops with the
        consumer, and the HTTP client is closed on the way out."""
        heartbeat.start()
        tasks = [consumer.run(stop)]
        if dispatch is not None:
            tasks.append(dispatch.run(stop))
        try:
            await asyncio.gather(*tasks)
        finally:
            heartbeat.stop()
            if self._http is not None:
                await self._http.aclose()
                self._http = None
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
        OtelTracing().start(self._settings.otlp_endpoint, "engineering-influence-worker")
        asyncio.run(self._main())

    async def _main(self) -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for number in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(number, stop.set)
        _LOGGER.info("worker starting")
        await self.serve(stop)
        _LOGGER.info("worker stopped")
