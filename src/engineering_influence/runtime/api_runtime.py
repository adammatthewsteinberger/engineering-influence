# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose and run the REST API."""

from collections.abc import Callable
from typing import Any

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
from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.infrastructure.security.token_bucket_rate_limiter import (
    TokenBucketRateLimiter,
)
from engineering_influence.interaction.api.api_guard import ApiGuard
from engineering_influence.interaction.api.api_observability import ApiObservability
from engineering_influence.interaction.api.application import ApiApplication
from engineering_influence.interfaces.secret_provider_port import SecretProviderPort
from engineering_influence.repositories.sqlmodel_ledger import SqlModelLedger
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.endpoint_checks import EndpointChecks
from engineering_influence.services.readiness_probe import ReadinessProbe


class ApiRuntime:
    """Build the API from settings and serve it.

    ``EI_API_KEYS`` is required: with no key the API cannot be built, so a
    misconfigured deployment stops instead of serving anonymously.
    """

    def __init__(
        self,
        settings: AppSettings,
        secrets: SecretProviderPort,
        server: Callable[..., None] | None = None,
    ) -> None:
        self._settings = settings
        self._secrets = secrets
        self._server = server
        self._ledger: SqlModelLedger | None = None

    def build_app(self) -> Any:
        """Wire the ledger, the correlating queue, the guard and observability."""
        correlation = ContextVarCorrelation()
        queue = CorrelatingQueue(
            RabbitMqQueueAdapter(self._settings.rabbitmq_url, self._settings.queue_name),
            correlation,
        )
        guard = ApiGuard(
            ConstantTimeApiKeyVerifier.from_secrets(self._secrets),
            TokenBucketRateLimiter(self._settings.rate_burst, self._settings.rate_per_second),
        )
        checks = (
            EndpointChecks.tcp("database", self._settings.database_url, 5432),
            EndpointChecks.tcp("rabbitmq", self._settings.rabbitmq_url, 5672),
        )
        readiness = ReadinessProbe(tuple(check for check in checks if check is not None))
        observability = ApiObservability(readiness, BootstrapMetrics(), correlation)
        self._ledger = SqlModelLedger(self._settings.database_url)
        return ApiApplication(self._ledger, queue, guard, observability).build()

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
        """Dispose of the database pool."""
        if self._ledger is not None:
            self._ledger.close()
            self._ledger = None

    @staticmethod
    def _uvicorn() -> Callable[..., None]:
        import uvicorn

        return uvicorn.run
