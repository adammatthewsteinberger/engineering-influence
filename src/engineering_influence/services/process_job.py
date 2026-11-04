# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Application service that turns one queued job into a recorded phase result."""

import asyncio
from typing import Any

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.contracts.job_outcome import JobOutcome
from engineering_influence.domain.gate import Gate
from engineering_influence.domain.gate_kind import GateKind
from engineering_influence.domain.phase_run import PhaseRun
from engineering_influence.domain.phase_state import PhaseState
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.ledger_port import LedgerPort
from engineering_influence.interfaces.queue_port import QueuePort
from engineering_influence.services.interfaces.process_job_interface import ProcessJobInterface
from engineering_influence.services.interfaces.run_phase_interface import RunPhaseInterface

_PREFIX = "pipeline."


class ProcessJob(ProcessJobInterface):
    """Run a stage, record it, then enqueue the next stage or finish the pipeline.

    Delivery is at least once. If a worker dies after the ledger write but before the
    broker acknowledges the job, the job runs again and records the stage twice.

    The ledger and queue ports are synchronous, and the RabbitMQ queue adapter starts its
    own event loop, which fails inside a running one. Both therefore run on a worker
    thread, which also keeps a slow database call from stalling the consumer.
    """

    def __init__(self, run_phase: RunPhaseInterface, ledger: LedgerPort, queue: QueuePort) -> None:
        self._run_phase = run_phase
        self._ledger = ledger
        self._queue = queue

    async def process(self, message: JobMessage) -> JobOutcome:
        """A human gate parks the pipeline here; an accepted stage moves it on."""
        if not message.kind.startswith(_PREFIX) or message.kind == _PREFIX:
            raise ApplicationError(
                code="UNKNOWN_JOB_KIND",
                message=f"cannot process job kind {message.kind!r}",
                http_status=422,
            )
        stage = message.kind.removeprefix(_PREFIX)
        payload = dict(message.payload)
        gate = self._gate(stage, payload)
        run, artifact = await self._run_phase.run(
            PhaseRun(message.job_id, message.kind, PhaseState.QUEUED),
            str(payload.get("artifact_type", stage)),
            gate,
            payload,
        )
        slug = str(payload.get("project_slug", ""))
        if run.state is PhaseState.AWAITING_GATE:
            self._ledger.append(
                "gate.awaiting",
                {
                    "job_id": message.job_id,
                    "phase": message.kind,
                    "gate": gate.name,
                    "project_slug": slug,
                },
            )
            return JobOutcome.AWAITING_GATE
        await asyncio.to_thread(
            self._ledger.append,
            "phase.completed",
            {
                "job_id": message.job_id,
                "phase": message.kind,
                "artifact_id": artifact.artifact_id,
                "project_slug": slug,
            },
        )
        remaining = self._remaining(payload)
        if not remaining:
            await asyncio.to_thread(
                self._ledger.append, "pipeline.completed", {"project_slug": slug}
            )
            return JobOutcome.PIPELINE_COMPLETED
        following, *rest = remaining
        await asyncio.to_thread(
            self._queue.enqueue,
            f"{_PREFIX}{following}",
            {**payload, "stage": following, "remaining_stages": rest},
        )
        return JobOutcome.COMPLETED

    @staticmethod
    def _gate(stage: str, payload: dict[str, Any]) -> Gate:
        return Gate(
            str(payload.get("gate_name", stage)),
            GateKind(str(payload.get("gate_kind", GateKind.AUTO))),
            str(payload.get("gate_rubric", "the artifact is not empty")),
        )

    @staticmethod
    def _remaining(payload: dict[str, Any]) -> list[str]:
        remaining = payload.get("remaining_stages", [])
        if not isinstance(remaining, list) or not all(isinstance(item, str) for item in remaining):
            raise ValueError("remaining_stages must be a list of stage names")
        return list(remaining)
