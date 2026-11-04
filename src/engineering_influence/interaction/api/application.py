# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""FastAPI interaction over the shared controller."""

from typing import TYPE_CHECKING, Any, cast

from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interaction.api.api_observability import ApiObservability
from engineering_influence.interaction.api.prometheus_renderer import PrometheusRenderer
from engineering_influence.interfaces.ledger_port import LedgerPort
from engineering_influence.interfaces.queue_port import QueuePort
from engineering_influence.services.start_pipeline import StartPipeline

if TYPE_CHECKING:
    from engineering_influence.interaction.api.api_guard import ApiGuard


class ApiApplication:
    """Builds the REST application without duplicating application logic.

    The guard is required: there is no way to construct an unauthenticated API.
    Observability is optional; when given it adds correlation ids, request counters,
    ``/health/live``, ``/health/ready`` and an authenticated ``/metrics``.
    """

    def __init__(
        self,
        ledger: LedgerPort,
        queue: QueuePort,
        guard: "ApiGuard",
        observability: ApiObservability | None = None,
    ) -> None:
        self._controller = ProjectController(StartPipeline(ledger, queue))
        self._guard = guard
        self._observability = observability
        self._renderer = PrometheusRenderer()

    def build(self) -> Any:
        """Return a FastAPI app with the public project-start contract."""
        from fastapi import Depends, FastAPI

        app = FastAPI(title="engineering-influence", version="0.1.0a1")
        app.add_exception_handler(ApplicationError, self._render_error)
        app.add_api_route(
            "/v1/pipelines",
            self._start,
            methods=["POST"],
            response_model=dict,
            dependencies=[Depends(self._guard)],
        )
        if self._observability is not None:
            self._add_observability(app, self._observability)
        return app

    def _add_observability(self, app: Any, observability: ApiObservability) -> None:
        from fastapi import Depends
        from vibey_bootstrap.fastapi_middleware import install_middleware

        from engineering_influence.interaction.api.request_context_middleware import (
            RequestContextMiddleware,
        )

        app.add_api_route("/health/live", self._live, methods=["GET"], response_model=None)
        app.add_api_route("/health/ready", self._ready, methods=["GET"], response_model=None)
        app.add_api_route(
            "/metrics",
            self._metrics,
            methods=["GET"],
            response_model=None,
            dependencies=[Depends(self._guard)],
        )
        # Added last, so it is outermost and the id is active for the timing log too.
        install_middleware(app, alert_subject_prefix="engineering-influence: ")
        app.add_middleware(
            RequestContextMiddleware,
            correlation=observability.correlation,
            metrics=observability.metrics,
        )

    def _start(self, request: ProjectRequest) -> dict[str, str]:
        response = self._controller.start(request)
        return response.model_dump()

    def _live(self) -> dict[str, str]:
        return {"status": "alive"}

    def _ready(self) -> Any:
        from fastapi.responses import JSONResponse

        report = cast(ApiObservability, self._observability).readiness.check()
        return JSONResponse(
            status_code=200 if report.ready else 503,
            content={"status": "ready" if report.ready else "unavailable"},
        )

    def _metrics(self) -> Any:
        from fastapi.responses import PlainTextResponse

        observability = cast(ApiObservability, self._observability)
        text = self._renderer.render(
            observability.metrics.counters(),
            observability.metrics.latencies(),
            observability.readiness.check(),
        )
        return PlainTextResponse(text, media_type="text/plain; version=0.0.4; charset=utf-8")

    def _render_error(self, _: Any, error: Exception) -> Any:
        from fastapi.responses import JSONResponse

        known = cast(ApplicationError, error)
        return JSONResponse(
            status_code=known.http_status,
            content={
                "code": known.code,
                "message": known.message,
                "retryable": known.retryable,
            },
        )
