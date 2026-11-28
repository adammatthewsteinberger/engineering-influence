# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""FastAPI interaction over the shared controller."""

from typing import TYPE_CHECKING, Any, cast

from engineering_influence import __version__
from engineering_influence.contracts.brief.v1.book_brief_v1 import BookBriefV1
from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.contracts.run.v1.run_grant_v1 import RunGrantV1
from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
from engineering_influence.controllers.interfaces.project_controller_interface import (
    ProjectControllerInterface,
)
from engineering_influence.controllers.interfaces.run_controller_interface import (
    RunControllerInterface,
)
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.api.api_observability import ApiObservability
from engineering_influence.interactions.api.interfaces.application_interface import (
    ApiApplicationInterface,
)
from engineering_influence.interactions.api.prometheus_renderer import PrometheusRenderer
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface
from engineering_influence.services.interfaces.run_management_interface import (
    RunManagementInterface,
)

if TYPE_CHECKING:
    from engineering_influence.interactions.api.api_guard import ApiGuard


class ApiApplication(ApiApplicationInterface):
    """Builds the REST application without duplicating application logic.

    The guard is required: there is no way to construct an unauthenticated API.
    Observability is optional; when given it adds correlation ids, request counters,
    ``/health/live``, ``/health/ready`` and an authenticated ``/metrics``.
    """

    def __init__(
        self,
        controller: ProjectControllerInterface,
        guard: "ApiGuard",
        observability: ApiObservability | None = None,
        runs: RunControllerInterface | None = None,
        creator: CreateRunInterface | None = None,
        manager: RunManagementInterface | None = None,
        metrics_guard: "ApiGuard | None" = None,
    ) -> None:
        """Remember the controller, the guard, and the optional observability, run, creator, manager and metrics guard."""
        self._controller = controller
        self._runs = runs
        self._creator = creator
        self._manager = manager
        self._guard = guard
        self._metrics_guard = metrics_guard or guard
        self._observability = observability
        self._renderer = PrometheusRenderer()

    def build(self) -> Any:
        """Return a FastAPI app with the public project-start contract."""
        from fastapi import Depends, FastAPI

        app = FastAPI(title="engineering-influence", version=__version__)
        app.add_exception_handler(ApplicationError, self._render_error)
        app.add_api_route(
            "/v1/pipelines",
            self._start,
            methods=["POST"],
            response_model=dict,
            dependencies=[Depends(self._guard)],
        )
        if self._runs is not None:
            self._add_run_routes(app)
        if self._creator is not None:
            app.add_api_route(
                "/v1/runs",
                self._create_run,
                methods=["POST"],
                response_model=RunSummaryV1,
                status_code=201,
                dependencies=[Depends(self._guard)],
            )
        if self._manager is not None:
            app.add_api_route(
                "/v1/runs",
                self._list_runs,
                methods=["GET"],
                response_model=list[RunSummaryV1],
                dependencies=[Depends(self._guard)],
            )
            app.add_api_route(
                "/v1/runs/{run_id}/resume",
                self._resume_run,
                methods=["POST"],
                response_model=RunSummaryV1,
                dependencies=[Depends(self._guard)],
            )
            app.add_api_route(
                "/v1/runs/{run_id}/cancel",
                self._cancel_run,
                methods=["POST"],
                response_model=RunSummaryV1,
                dependencies=[Depends(self._guard)],
            )
            app.add_api_route(
                "/v1/runs/{run_id}/grant",
                self._grant_run,
                methods=["POST"],
                response_model=RunSummaryV1,
                dependencies=[Depends(self._guard)],
            )
            app.add_api_route(
                "/v1/runs/{run_id}/deny",
                self._deny_run,
                methods=["POST"],
                response_model=RunSummaryV1,
                dependencies=[Depends(self._guard)],
            )
        if self._observability is not None:
            self._add_observability(app, self._observability)
        return app

    def _add_run_routes(self, app: Any) -> None:
        from fastapi import Depends
        from fastapi.responses import Response

        app.add_api_route(
            "/v1/runs/{run_id}",
            self._run_summary,
            methods=["GET"],
            response_model=RunSummaryV1,
            dependencies=[Depends(self._guard)],
        )
        app.add_api_route(
            "/v1/runs/{run_id}/artifacts/{name:path}",
            self._run_artifact,
            methods=["GET"],
            response_class=Response,
            dependencies=[Depends(self._guard)],
        )

    def _add_observability(self, app: Any, observability: ApiObservability) -> None:
        from fastapi import Depends
        from vibey_bootstrap.fastapi_middleware import install_middleware

        from engineering_influence.interactions.api.request_context_middleware import (
            RequestContextMiddleware,
        )

        app.add_api_route("/health/live", self._live, methods=["GET"], response_model=None)
        app.add_api_route("/health/ready", self._ready, methods=["GET"], response_model=None)
        app.add_api_route(
            "/metrics",
            self._metrics,
            methods=["GET"],
            response_model=None,
            dependencies=[Depends(self._metrics_guard)],
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

    def _create_run(self, brief: BookBriefV1) -> RunSummaryV1:
        run = cast(CreateRunInterface, self._creator).create(brief.to_model())
        return RunSummaryV1.from_run(run, [])

    def _list_runs(self) -> list[RunSummaryV1]:
        manager = cast(RunManagementInterface, self._manager)
        return [RunSummaryV1.from_run(run, []) for run in manager.runs()]

    def _resume_run(self, run_id: str) -> RunSummaryV1:
        return RunSummaryV1.from_run(cast(RunManagementInterface, self._manager).resume(run_id), [])

    def _cancel_run(self, run_id: str) -> RunSummaryV1:
        return RunSummaryV1.from_run(cast(RunManagementInterface, self._manager).cancel(run_id), [])

    def _grant_run(self, run_id: str, grant: RunGrantV1 | None = None) -> RunSummaryV1:
        micro_usd = None if grant is None else grant.micro_usd
        return RunSummaryV1.from_run(
            cast(RunManagementInterface, self._manager).grant(run_id, micro_usd), []
        )

    def _deny_run(self, run_id: str) -> RunSummaryV1:
        return RunSummaryV1.from_run(cast(RunManagementInterface, self._manager).deny(run_id), [])

    def _run_summary(self, run_id: str) -> RunSummaryV1:
        return cast(RunControllerInterface, self._runs).summary(run_id)

    def _run_artifact(self, run_id: str, name: str) -> Any:
        from fastapi.responses import Response

        return Response(
            content=cast(RunControllerInterface, self._runs).artifact(run_id, name),
            media_type="application/octet-stream",
            headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store"},
        )

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
