# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The webhook events of a run's transitions, using the names and payload keys of the v1 catalogue."""

from engineering_influence.models.book_run import BookRun
from engineering_influence.models.outbox_event import OutboxEvent
from engineering_influence.services.interfaces.run_event_builder_interface import (
    RunEventBuilderInterface,
)


class RunEventBuilder(RunEventBuilderInterface):
    """One event per receiver URL, so each receiver gets its own copy and its own retries. With no URL configured,
    every transition produces no event, and nothing is queued.

    Ids are deterministic (run, event, stage and receiver), so a stage that is delivered twice queues each event once.
    The job id is the run and stage; the artifact id is the stage's output file; the project is the run.
    """

    GATE: str = "spend-consent"

    def __init__(self, urls: tuple[str, ...]) -> None:
        self._urls = urls

    def started(self, run: BookRun) -> tuple[OutboxEvent, ...]:
        """pipeline.started, with the stages still to run."""
        remaining = len(run.plan.stages)
        return self._events(
            run,
            "pipeline.started",
            run.stage,
            {"project_slug": run.run_id, "remaining_stages": remaining, "stage": run.stage},
        )

    def phase_completed(self, run: BookRun, stage: str) -> tuple[OutboxEvent, ...]:
        """phase.completed for the stage that just finished."""
        return self._events(
            run,
            "phase.completed",
            stage,
            {
                "artifact_id": f"{run.run_id}/{stage}.md",
                "job_id": f"{run.run_id}/{stage}",
                "phase": stage,
                "project_slug": run.run_id,
            },
        )

    def awaiting_gate(self, run: BookRun, stage: str) -> tuple[OutboxEvent, ...]:
        """gate.awaiting for the spend decision the run needs."""
        return self._events(
            run,
            "gate.awaiting",
            stage,
            {
                "gate": self.GATE,
                "job_id": f"{run.run_id}/{stage}",
                "phase": stage,
                "project_slug": run.run_id,
            },
        )

    def completed(self, run: BookRun) -> tuple[OutboxEvent, ...]:
        """pipeline.completed."""
        return self._events(run, "pipeline.completed", "", {"project_slug": run.run_id})

    def _events(
        self, run: BookRun, name: str, stage: str, payload: dict[str, object]
    ) -> tuple[OutboxEvent, ...]:
        return tuple(
            OutboxEvent(
                event_id=f"{run.run_id}:{name}:{stage}:{index}",
                url=url,
                event_name=name,
                payload=dict(payload),
            )
            for index, url in enumerate(self._urls)
        )
