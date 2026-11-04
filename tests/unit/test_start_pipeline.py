"""Tests for the first application flow."""

from engineering_influence.domain.governing_postulates import GoverningPostulates
from engineering_influence.domain.pipeline_stage import PipelineStage
from engineering_influence.domain.project import Project
from engineering_influence.interfaces.ledger_port import LedgerPort
from engineering_influence.interfaces.queue_port import QueuePort
from engineering_influence.services.start_pipeline import StartPipeline


class RecordingLedger(LedgerPort):
    """In-memory ledger fake for the service test."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def append(self, event_name: str, payload: dict[str, object]) -> None:
        self.events.append((event_name, payload))


class RecordingQueue(QueuePort):
    """In-memory queue fake for the service test."""

    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict[str, object]]] = []

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        self.jobs.append((kind, payload))
        return "job-1"


def test_start_pipeline_records_event_before_enqueue() -> None:
    ledger = RecordingLedger()
    queue = RecordingQueue()
    project = Project("demo", "Demo", GoverningPostulates(("Evidence.",)), (PipelineStage.THESIS,))

    assert StartPipeline(ledger, queue).start(project) == "job-1"
    assert ledger.events[0][0] == "pipeline.started"
    assert queue.jobs[0][0] == "pipeline.thesis"
