"""Routing queued jobs by kind, and handing ``run.advance`` jobs to the run advancer."""

import asyncio
from typing import Any

import pytest

from engineering_influence.contracts.job_message import JobMessage
from engineering_influence.contracts.job_outcome import JobOutcome
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.services.interfaces.advance_run_interface import AdvanceRunInterface
from engineering_influence.services.interfaces.process_job_interface import ProcessJobInterface
from engineering_influence.services.job_router import JobRouter
from engineering_influence.services.process_run_job import ProcessRunJob


class Advancer(AdvanceRunInterface):
    def __init__(self, outcome: AdvanceOutcome = AdvanceOutcome.ADVANCED) -> None:
        self.outcome = outcome
        self.calls: list[tuple[str, str, int]] = []

    async def advance(self, run_id: str, stage: str, attempt: int) -> AdvanceOutcome:
        self.calls.append((run_id, stage, attempt))
        return self.outcome


class Handler(ProcessJobInterface):
    def __init__(self, outcome: JobOutcome) -> None:
        self.outcome = outcome
        self.seen: list[str] = []

    async def process(self, message: JobMessage) -> JobOutcome:
        self.seen.append(message.kind)
        return self.outcome


def message(kind: str = "run.advance", **payload: Any) -> JobMessage:
    body = {"run_id": "run-1", "stage": "draft", "attempt": 2, **payload}
    return JobMessage(job_id="job-1", kind=kind, payload=body)


def process(job: ProcessJobInterface, item: JobMessage) -> JobOutcome:
    return asyncio.run(job.process(item))


def test_a_run_advance_job_calls_the_advancer_with_its_payload() -> None:
    advancer = Advancer()
    assert process(ProcessRunJob(advancer), message()) is JobOutcome.RUN_ADVANCED
    assert advancer.calls == [("run-1", "draft", 2)]


def test_extra_payload_keys_such_as_a_correlation_id_are_ignored() -> None:
    advancer = Advancer()
    process(ProcessRunJob(advancer), message(correlation_id="abc", note="x"))
    assert advancer.calls == [("run-1", "draft", 2)]


@pytest.mark.parametrize("outcome", list(AdvanceOutcome))
def test_every_advance_outcome_has_a_job_outcome_for_the_metrics(outcome: AdvanceOutcome) -> None:
    result = process(ProcessRunJob(Advancer(outcome)), message())
    assert result.value == f"run_{outcome.value}"


@pytest.mark.parametrize(
    "payload",
    [
        {"run_id": None},
        {"run_id": ""},
        {"run_id": "  "},
        {"run_id": 7},
        {"stage": None},
        {"stage": ""},
        {"stage": 3},
        {"attempt": None},
        {"attempt": 0},
        {"attempt": -1},
        {"attempt": "2"},
        {"attempt": 1.5},
        {"attempt": True},
    ],
)
def test_a_payload_that_cannot_name_a_delivery_is_refused(payload: dict[str, Any]) -> None:
    advancer = Advancer()
    with pytest.raises(ApplicationError) as raised:
        process(ProcessRunJob(advancer), message(**payload))
    assert (raised.value.code, raised.value.http_status) == ("INVALID_JOB_PAYLOAD", 422)
    assert advancer.calls == []


def test_a_payload_missing_a_key_is_refused() -> None:
    incomplete = JobMessage(job_id="job-1", kind="run.advance", payload={"run_id": "run-1"})
    with pytest.raises(ApplicationError) as raised:
        process(ProcessRunJob(Advancer()), incomplete)
    assert raised.value.code == "INVALID_JOB_PAYLOAD"


def test_the_run_service_only_handles_run_advance() -> None:
    with pytest.raises(ApplicationError) as raised:
        process(ProcessRunJob(Advancer()), message("run.cancel"))
    assert (raised.value.code, raised.value.http_status) == ("UNKNOWN_JOB_KIND", 422)


def test_the_router_sends_each_kind_to_the_handler_for_its_prefix() -> None:
    pipeline, runs = Handler(JobOutcome.COMPLETED), Handler(JobOutcome.RUN_SKIPPED)
    router = JobRouter({"pipeline": pipeline, "run": runs})
    assert process(router, message("pipeline.thesis")) is JobOutcome.COMPLETED
    assert process(router, message("run.advance")) is JobOutcome.RUN_SKIPPED
    assert (pipeline.seen, runs.seen) == (["pipeline.thesis"], ["run.advance"])


@pytest.mark.parametrize("kind", ["other.thing", "pipelines.thesis", "run", "x"])
def test_a_kind_nobody_handles_is_refused(kind: str) -> None:
    router = JobRouter({"pipeline": Handler(JobOutcome.COMPLETED)})
    with pytest.raises(ApplicationError) as raised:
        process(router, message(kind))
    assert (raised.value.code, raised.value.http_status) == ("UNKNOWN_JOB_KIND", 422)
    assert kind in raised.value.message


def test_the_router_does_not_change_when_its_routes_dictionary_does() -> None:
    routes: dict[str, ProcessJobInterface] = {"run": Handler(JobOutcome.RUN_SKIPPED)}
    router = JobRouter(routes)
    routes.clear()
    assert process(router, message("run.advance")) is JobOutcome.RUN_SKIPPED
