"""FastAPI interaction over the shared controller."""

from typing import Any

from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.interfaces.ledger_port import LedgerPort
from engineering_influence.interfaces.queue_port import QueuePort
from engineering_influence.services.start_pipeline import StartPipeline


class ApiApplication:
    """Builds the REST application without duplicating application logic."""

    def __init__(self, ledger: LedgerPort, queue: QueuePort) -> None:
        self._controller = ProjectController(StartPipeline(ledger, queue))

    def build(self) -> Any:
        """Return a FastAPI app with the public project-start contract."""
        from fastapi import FastAPI

        app = FastAPI(title="engineering-influence", version="0.1.0a1")
        app.add_api_route("/v1/pipelines", self._start, methods=["POST"], response_model=dict)
        return app

    def _start(self, request: ProjectRequest) -> dict[str, str]:
        response = self._controller.start(request)
        return response.model_dump()
