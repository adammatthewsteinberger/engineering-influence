# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose and run the job worker."""

import asyncio
import logging
import signal

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
from engineering_influence.repositories.sqlmodel_ledger import SqlModelLedger
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.services.process_job import ProcessJob
from engineering_influence.services.run_phase import RunPhase

_LOGGER = logging.getLogger(__name__)


class WorkerRuntime:
    """Build the worker from settings and consume until a stop signal.

    The runner and gate are deterministic placeholders: this process exercises the whole
    pipeline offline. A model-backed runner replaces ``DeterministicRunner`` here.
    """

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._ledger: SqlModelLedger | None = None

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
        self._ledger = SqlModelLedger(self._settings.database_url)
        process_job = ProcessJob(
            TracedRunPhase(RunPhase(DeterministicRunner(), NonEmptyArtifactGate())),
            self._ledger,
            queue,
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
        """Dispose of the database pool."""
        if self._ledger is not None:
            self._ledger.close()
            self._ledger = None

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
