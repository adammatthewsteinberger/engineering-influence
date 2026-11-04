# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Start-pipeline application service."""

from engineering_influence.domain.project import Project
from engineering_influence.interfaces.ledger_port import LedgerPort
from engineering_influence.interfaces.queue_port import QueuePort
from engineering_influence.services.interfaces.start_pipeline_interface import (
    StartPipelineInterface,
)


class StartPipeline(StartPipelineInterface):
    """Coordinates the first durable pipeline event and job."""

    def __init__(self, ledger: LedgerPort, queue: QueuePort) -> None:
        self._ledger = ledger
        self._queue = queue

    def start(self, project: Project) -> str:
        """Write `PipelineStarted`, then enqueue the first selected stage."""
        first_stage = project.stages[0].value
        payload: dict[str, object] = {"project_slug": project.slug, "stage": first_stage}
        self._ledger.append("pipeline.started", payload)
        return self._queue.enqueue(f"pipeline.{first_stage}", payload)
