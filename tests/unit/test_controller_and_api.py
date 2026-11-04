"""Contract tests for the shared controller and REST adapter."""

import pytest

from engineering_influence.contracts.project_request import ProjectRequest
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.interaction.api.application import ApiApplication
from engineering_influence.interfaces.ledger_port import LedgerPort
from engineering_influence.interfaces.queue_port import QueuePort
from engineering_influence.services.start_pipeline import StartPipeline


class RecordingLedger(LedgerPort):
    """In-memory ledger for interaction tests."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def append(self, event_name: str, payload: dict[str, object]) -> None:
        self.events.append((event_name, payload))


class RecordingQueue(QueuePort):
    """In-memory queue for interaction tests."""

    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict[str, object]]] = []

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        self.jobs.append((kind, payload))
        return "job-api-1"


def request() -> ProjectRequest:
    return ProjectRequest(
        slug="demo",
        title="Demo",
        postulates=("Evidence first.",),
        stages=("thesis",),
    )


def test_controller_uses_shared_start_pipeline_service() -> None:
    ledger = RecordingLedger()
    queue = RecordingQueue()

    result = ProjectController(StartPipeline(ledger, queue)).start(request())

    assert result.model_dump() == {"job_id": "job-api-1", "project_slug": "demo"}
    assert ledger.events[0][0] == "pipeline.started"


def test_api_returns_same_controller_contract() -> None:
    application = ApiApplication(RecordingLedger(), RecordingQueue())
    application.build()

    assert application._start(request()) == {"job_id": "job-api-1", "project_slug": "demo"}


def test_api_rejects_extra_request_fields() -> None:
    with pytest.raises(ValueError):
        ProjectRequest(**{**request().model_dump(), "extra": True})
