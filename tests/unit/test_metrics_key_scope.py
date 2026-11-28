# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A metrics key opens /metrics only: /metrics uses its own guard when one is given, and the runtime falls back to the
main guard when no metrics keys are configured."""

from collections.abc import Mapping
from types import SimpleNamespace

import pytest
from test_controller_and_api import RecordingLedger, RecordingQueue

from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.observability.bootstrap_metrics import BootstrapMetrics
from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.interactions.api.api_guard import ApiGuard
from engineering_influence.interactions.api.api_observability import ApiObservability
from engineering_influence.interactions.api.application import ApiApplication
from engineering_influence.interfaces.rate_limiter_interface import RateLimiterInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.runtime.api_runtime import ApiRuntime
from engineering_influence.services.readiness_probe import ReadinessProbe
from engineering_influence.services.start_pipeline import StartPipeline


def observed() -> ApiObservability:
    from engineering_influence.infrastructure.observability.context_var_correlation import (
        ContextVarCorrelation,
    )

    return ApiObservability(ReadinessProbe(()), BootstrapMetrics(), ContextVarCorrelation())


MAIN = "main-api-key-of-at-least-24-characters"
METRICS = "metrics-key-of-at-least-24-characters"


class Unlimited(RateLimiterInterface):
    def allow(self, key: str) -> bool:
        return True


class Secrets(SecretProviderInterface):
    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = values

    def require(self, name: str) -> str:
        if name not in self._values:
            raise ApplicationError(
                code="SECRET_MISSING", message=f"{name} is not set", http_status=503
            )
        return self._values[name]


def guard(key: str) -> ApiGuard:
    return ApiGuard(ConstantTimeApiKeyVerifier([key]), Unlimited())


def metrics_route_guard(application: ApiApplication) -> object:
    app = application.build()
    route = next(r for r in app.routes if getattr(r, "path", "") == "/metrics")
    return route.dependencies[0].dependency


def test_the_metrics_route_uses_the_metrics_guard_when_one_is_given() -> None:
    main, scoped = guard(MAIN), guard(METRICS)
    application = ApiApplication(
        ProjectController(StartPipeline(RecordingLedger(), RecordingQueue())),
        main,
        observability=observed(),
        metrics_guard=scoped,
    )
    assert metrics_route_guard(application) is scoped


def test_the_metrics_route_uses_the_main_guard_without_a_metrics_guard() -> None:
    main = guard(MAIN)
    application = ApiApplication(
        ProjectController(StartPipeline(RecordingLedger(), RecordingQueue())),
        main,
        observability=observed(),
    )
    assert metrics_route_guard(application) is main


def runtime_with(values: Mapping[str, str]) -> SimpleNamespace:
    settings = SimpleNamespace(rate_burst=30.0, rate_per_second=10.0)
    return SimpleNamespace(_secrets=Secrets(values), _settings=settings)


def test_without_metrics_keys_the_main_guard_serves_metrics() -> None:
    main = guard(MAIN)
    assert ApiRuntime._metrics_guard(runtime_with({"EI_API_KEYS": MAIN}), main) is main


def test_with_metrics_keys_only_they_open_metrics() -> None:
    main = guard(MAIN)
    scoped = ApiRuntime._metrics_guard(runtime_with({"EI_METRICS_API_KEYS": METRICS}), main)
    assert scoped is not main
    assert scoped._verifier.verify(METRICS) is True  # type: ignore[attr-defined]
    assert scoped._verifier.verify(MAIN) is False  # type: ignore[attr-defined]


def test_a_metrics_key_that_is_not_a_secret_error_is_raised() -> None:
    class Broken(SecretProviderInterface):
        def require(self, name: str) -> str:
            raise ApplicationError(code="SOMETHING_ELSE", message="broken", http_status=500)

    with pytest.raises(ApplicationError):
        ApiRuntime._metrics_guard(
            SimpleNamespace(
                _secrets=Broken(), _settings=SimpleNamespace(rate_burst=1.0, rate_per_second=1.0)
            ),
            guard(MAIN),
        )
