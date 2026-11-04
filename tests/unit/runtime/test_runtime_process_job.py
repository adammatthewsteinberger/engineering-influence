"""Job processing: advancing, parking, and surviving a hostile event loop."""

import asyncio
import threading
from typing import Any

import pytest

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.contracts.job_outcome import JobOutcome
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.deterministic_runner import DeterministicRunner
from engineering_influence.infrastructure.non_empty_artifact_gate import NonEmptyArtifactGate
from engineering_influence.interfaces.ledger_port import LedgerPort
from engineering_influence.interfaces.queue_port import QueuePort
from engineering_influence.interfaces.runner_port import RunnerPort
from engineering_influence.services.process_job import ProcessJob
from engineering_influence.services.run_phase import RunPhase


class Ledger(LedgerPort):
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []
        self.threads: list[str] = []

    def append(self, event_name: str, payload: dict[str, object]) -> None:
        self.threads.append(threading.current_thread().name)
        self.events.append((event_name, payload))


class Queue(QueuePort):
    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict[str, object]]] = []

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        self.jobs.append((kind, payload))
        return f"job-{len(self.jobs)}"


class LoopHostileQueue(QueuePort):
    """Behaves like the RabbitMQ adapter: it starts its own event loop to publish."""

    def __init__(self) -> None:
        self.kinds: list[str] = []

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        async def publish() -> None:
            self.kinds.append(kind)

        asyncio.run(publish())
        return "job"


class BlankRunner(RunnerPort):
    async def run(self, phase: str, context: dict[str, object]) -> str:
        return "   "


def service(
    queue: QueuePort | None = None, runner: RunnerPort | None = None
) -> tuple[ProcessJob, Ledger, Any]:
    ledger = Ledger()
    queue = queue or Queue()
    job = ProcessJob(
        RunPhase(runner or DeterministicRunner(), NonEmptyArtifactGate()), ledger, queue
    )
    return job, ledger, queue


def message(kind: str = "pipeline.thesis", **payload: Any) -> JobMessage:
    return JobMessage(job_id="job-0", kind=kind, payload={"project_slug": "demo", **payload})


def test_a_completed_stage_enqueues_the_next_one_and_keeps_the_payload() -> None:
    job, ledger, queue = service()

    outcome = asyncio.run(
        job.process(message(remaining_stages=["book", "publish"], correlation_id="abc-12345"))
    )

    assert outcome is JobOutcome.COMPLETED
    kind, payload = queue.jobs[0]
    assert kind == "pipeline.book"
    assert payload["stage"] == "book"
    assert payload["remaining_stages"] == ["publish"]
    assert payload["correlation_id"] == "abc-12345"
    assert payload["project_slug"] == "demo"
    assert [name for name, _ in ledger.events] == ["phase.completed"]


def test_the_last_stage_finishes_the_pipeline() -> None:
    job, ledger, queue = service()

    outcome = asyncio.run(job.process(message("pipeline.publish", remaining_stages=[])))

    assert outcome is JobOutcome.PIPELINE_COMPLETED
    assert queue.jobs == []
    assert [name for name, _ in ledger.events] == ["phase.completed", "pipeline.completed"]
    assert ledger.events[-1][1] == {"project_slug": "demo"}


def test_a_job_with_no_remaining_stages_field_is_the_last_stage() -> None:
    job, _, queue = service()

    assert asyncio.run(job.process(message())) is JobOutcome.PIPELINE_COMPLETED
    assert queue.jobs == []


def test_the_completion_record_names_the_job_and_artifact() -> None:
    job, ledger, _ = service()

    asyncio.run(job.process(message()))

    assert ledger.events[0] == (
        "phase.completed",
        {
            "job_id": "job-0",
            "phase": "pipeline.thesis",
            "artifact_id": "job-0:pipeline.thesis",
            "project_slug": "demo",
        },
    )


def test_a_human_gate_parks_the_pipeline() -> None:
    job, ledger, queue = service()

    outcome = asyncio.run(
        job.process(
            message(
                gate_name="editor-review",
                gate_kind="human",
                gate_rubric="a person approves",
                remaining_stages=["book"],
            )
        )
    )

    assert outcome is JobOutcome.AWAITING_GATE
    assert queue.jobs == []
    assert ledger.events == [
        (
            "gate.awaiting",
            {
                "job_id": "job-0",
                "phase": "pipeline.thesis",
                "gate": "editor-review",
                "project_slug": "demo",
            },
        )
    ]


def test_a_rejected_automatic_gate_also_parks_the_pipeline() -> None:
    job, ledger, queue = service(runner=BlankRunner())

    outcome = asyncio.run(job.process(message(remaining_stages=["book"])))

    assert outcome is JobOutcome.AWAITING_GATE
    assert queue.jobs == []
    assert ledger.events[0][0] == "gate.awaiting"


def test_the_artifact_type_comes_from_the_payload_when_given() -> None:
    job, ledger, _ = service()

    asyncio.run(job.process(message(artifact_type="argument-inventory")))

    assert ledger.events[0][1]["artifact_id"] == "job-0:pipeline.thesis"


@pytest.mark.parametrize("kind", ["thesis", "other.thesis", "pipeline."])
def test_a_job_kind_that_is_not_a_pipeline_stage_is_refused(kind: str) -> None:
    job, ledger, _ = service()

    with pytest.raises(ApplicationError) as caught:
        asyncio.run(job.process(message(kind)))

    assert caught.value.code == "UNKNOWN_JOB_KIND"
    assert ledger.events == []


def test_an_unknown_gate_kind_is_an_error() -> None:
    job, _, _ = service()

    with pytest.raises(ValueError):
        asyncio.run(job.process(message(gate_kind="robot")))


@pytest.mark.parametrize("remaining", ["book", [1, 2], {"a": 1}])
def test_malformed_remaining_stages_are_an_error(remaining: Any) -> None:
    job, ledger, queue = service()

    with pytest.raises(ValueError, match="remaining_stages"):
        asyncio.run(job.process(message(remaining_stages=remaining)))

    assert queue.jobs == []
    assert [name for name, _ in ledger.events] == ["phase.completed"]


def test_blocking_ports_run_off_the_event_loop_thread() -> None:
    job, ledger, _ = service(queue=LoopHostileQueue())

    outcome = asyncio.run(job.process(message(remaining_stages=["book"])))

    assert outcome is JobOutcome.COMPLETED
    assert ledger.threads and all(name != "MainThread" for name in ledger.threads)


def test_a_queue_that_starts_its_own_loop_works_from_the_worker() -> None:
    queue = LoopHostileQueue()
    job, _, _ = service(queue=queue)

    asyncio.run(job.process(message(remaining_stages=["book"])))

    assert queue.kinds == ["pipeline.book"]


def test_the_placeholder_runner_and_gate_are_deterministic() -> None:
    runner = DeterministicRunner()

    first = asyncio.run(runner.run("pipeline.thesis", {"project_slug": "demo"}))
    second = asyncio.run(runner.run("pipeline.thesis", {"project_slug": "demo"}))

    assert first == second == "pipeline.thesis: draft for demo"
    assert asyncio.run(runner.run("p", {})) == "p: draft for project"
