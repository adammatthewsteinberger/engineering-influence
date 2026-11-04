# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""FastAPI interaction over the shared controller."""

from typing import TYPE_CHECKING, Any, cast

from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.ledger_port import LedgerPort
from engineering_influence.interfaces.queue_port import QueuePort
from engineering_influence.services.start_pipeline import StartPipeline

if TYPE_CHECKING:
    from engineering_influence.interaction.api.api_guard import ApiGuard


class ApiApplication:
    """Builds the REST application without duplicating application logic.

    The guard is required: there is no way to construct an unauthenticated API.
    """

    def __init__(self, ledger: LedgerPort, queue: QueuePort, guard: "ApiGuard") -> None:
        self._controller = ProjectController(StartPipeline(ledger, queue))
        self._guard = guard

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
        return app

    def _start(self, request: ProjectRequest) -> dict[str, str]:
        response = self._controller.start(request)
        return response.model_dump()

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
