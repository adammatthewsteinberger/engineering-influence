# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose and run the REST API."""

from collections.abc import Callable
from typing import Any

from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.controllers.run_controller import RunController
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.object_storage.s3_artifact_store import S3ArtifactStore
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
from engineering_influence.infrastructure.rabbitmq_queue import RabbitMqQueueAdapter
from engineering_influence.infrastructure.schema_migrator import SchemaMigrator
from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.infrastructure.security.token_bucket_rate_limiter import (
    TokenBucketRateLimiter,
)
from engineering_influence.interactions.api.api_guard import ApiGuard
from engineering_influence.interactions.api.api_observability import ApiObservability
from engineering_influence.interactions.api.application import ApiApplication
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.interfaces.schema_migrator_interface import SchemaMigratorInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_ledger import SqlModelLedger
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.artifact_store_factory import ArtifactStoreFactory
from engineering_influence.runtime.endpoint_checks import EndpointChecks
from engineering_influence.runtime.interfaces.api_runtime_interface import ApiRuntimeInterface
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.list_runs import ListRuns
from engineering_influence.services.read_run import ReadRun
from engineering_influence.services.readiness_probe import ReadinessProbe
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.resume_run import ResumeRun
from engineering_influence.services.run_management import RunManagement
from engineering_influence.services.spend_ceiling import SpendCeiling
from engineering_influence.services.start_pipeline import StartPipeline


class ApiRuntime(ApiRuntimeInterface):
    """Build the API from settings and serve it.

    ``EI_API_KEYS`` is required: with no key the API cannot be built, so a
    misconfigured deployment stops instead of serving anonymously.
    """

    def __init__(
        self,
        settings: AppSettings,
        secrets: SecretProviderInterface,
        server: Callable[..., None] | None = None,
        queue: QueueInterface | None = None,
        migrator: SchemaMigratorInterface | None = None,
    ) -> None:
        self._settings = settings
        self._secrets = secrets
        self._server = server
        self._queue = queue
        self._migrator = migrator or SchemaMigrator()
        self._ledger: SqlModelLedger | None = None
        self._stores: list[SqlModelRunRepository | SqlModelArtifactStore | S3ArtifactStore] = []

    def build_app(self) -> Any:
        """Wire the ledger, the correlating queue, the guard and observability."""
        correlation = ContextVarCorrelation()
        queue = CorrelatingQueue(
            self._queue
            or RabbitMqQueueAdapter(self._settings.rabbitmq_url, self._settings.queue_name),
            correlation,
        )
        guard = ApiGuard(
            ConstantTimeApiKeyVerifier.from_secrets(self._secrets),
            TokenBucketRateLimiter(self._settings.rate_burst, self._settings.rate_per_second),
        )
        metrics_guard = self._metrics_guard(guard)
        checks = (
            EndpointChecks.tcp("database", self._settings.database_url, 5432),
            EndpointChecks.tcp("rabbitmq", self._settings.rabbitmq_url, 5672),
        )
        readiness = ReadinessProbe(tuple(check for check in checks if check is not None))
        observability = ApiObservability(readiness, BootstrapMetrics(), correlation)
        self._migrator.check(self._settings.database_url)
        self._ledger = SqlModelLedger(self._settings.database_url)
        controller = ProjectController(StartPipeline(self._ledger, queue))
        url = self._settings.database_url
        runs, artifacts = SqlModelRunRepository(url), ArtifactStoreFactory().build(self._settings)
        self._stores = [runs, artifacts]
        run_controller = RunController(ReadRun(runs, artifacts))
        ceiling = SpendCeiling(runs, self._settings.spend_limits)
        creator = CreateRun(runs, queue, ceiling=ceiling)
        manager = RunManagement(
            ListRuns(runs),
            ResumeRun(runs, queue),
            CancelRun(runs),
            ResolveSpendConsent(runs, queue, ceiling),
        )
        return ApiApplication(
            controller,
            guard,
            observability,
            run_controller,
            creator,
            manager,
            metrics_guard=metrics_guard,
        ).build()

    def _metrics_guard(self, guard: ApiGuard) -> ApiGuard:
        """The guard for /metrics: the dedicated EI_METRICS_API_KEYS when they are set, else the main guard.

        A metrics key opens /metrics only; it is refused on every other route, so a scraper's key cannot run the API.
        """
        try:
            metrics = ConstantTimeApiKeyVerifier.from_secrets(self._secrets, "EI_METRICS_API_KEYS")
        except ApplicationError as error:
            if error.code != "SECRET_MISSING":
                raise
            return guard
        return ApiGuard(
            metrics,
            TokenBucketRateLimiter(self._settings.rate_burst, self._settings.rate_per_second),
        )

    def run(self) -> None:
        """Configure logging, build the app, and serve until stopped."""
        JsonLoggingConfigurator(self._settings.log_level).configure()
        ProcessCrashHooks().install()
        app = self.build_app()
        serve = self._server or self._uvicorn()
        try:
            # log_config=None leaves uvicorn's loggers on the root JSON handler.
            serve(app, host=self._settings.host, port=self._settings.port, log_config=None)
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
    def _uvicorn() -> Callable[..., None]:
        import uvicorn

        return uvicorn.run
