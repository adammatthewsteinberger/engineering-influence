"""The ``run`` command group."""

import argparse
import json
from pathlib import Path

import pytest

from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
from engineering_influence.controllers.interfaces.run_controller_interface import (
    RunControllerInterface,
)
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.interactions.cli.run_cli import RunCli
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.runtime.cli_runtime import CliRuntime
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface
from engineering_influence.services.interfaces.resume_run_interface import ResumeRunInterface


def a_run(status: RunStatus = RunStatus.PARKED_CAPACITY) -> BookRun:
    brief = BookBrief(kind=BookKind.NONFICTION, idea="sourdough", budget_micro_usd=1_000)
    plan = StagePlan(kind=BookKind.NONFICTION, stages=("brief", "outline"))
    return BookRun("run-1", brief, plan, Budget(cap=1_000), stage="outline", status=status)


class Resumer(ResumeRunInterface):
    def __init__(self, failure: BaseException | None = None) -> None:
        self.failure = failure
        self.seen: list[str] = []

    def resume(self, run_id: str) -> BookRun:
        if self.failure is not None:
            raise self.failure
        self.seen.append(run_id)
        return a_run(RunStatus.RUNNING)


class Canceller(CancelRunInterface):
    def __init__(self, failure: BaseException | None = None) -> None:
        self.failure = failure
        self.seen: list[str] = []

    def cancel(self, run_id: str) -> BookRun:
        if self.failure is not None:
            raise self.failure
        self.seen.append(run_id)
        return a_run(RunStatus.CANCELLED)


class Reader(RunControllerInterface):
    def __init__(self, failure: BaseException | None = None) -> None:
        self.failure = failure

    def summary(self, run_id: str) -> RunSummaryV1:
        if self.failure is not None:
            raise self.failure
        return RunSummaryV1.from_run(a_run(RunStatus.RUNNING), ["brief.md"])

    def artifact(self, run_id: str, name: str) -> bytes:
        raise NotImplementedError


def cli(
    resumer: Resumer | None = None,
    canceller: Canceller | None = None,
    reader: Reader | None = None,
) -> RunCli:
    return RunCli(
        lambda: resumer or Resumer(),
        lambda: canceller or Canceller(),
        lambda: reader or Reader(),
    )


def status_args() -> argparse.Namespace:
    return argparse.Namespace(run_command="status", run_id="run-1")


def resume_args() -> argparse.Namespace:
    return argparse.Namespace(run_command="resume", run_id="run-1")


def cancel_args() -> argparse.Namespace:
    return argparse.Namespace(run_command="cancel", run_id="run-1")


def test_resuming_reports_the_run_and_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    resumer = Resumer()
    assert cli(resumer).run(resume_args()) == 0
    assert resumer.seen == ["run-1"]
    assert capsys.readouterr().out.strip() == (
        "run run-1 is running at stage 'outline'; its next stage is queued"
    )


def test_cancelling_reports_the_run_and_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    canceller = Canceller()
    assert cli(canceller=canceller).run(cancel_args()) == 0
    assert canceller.seen == ["run-1"]
    assert capsys.readouterr().out.strip() == "run run-1 is cancelled"


@pytest.mark.parametrize("code", ["RUN_NOT_FOUND", "RUN_FINISHED", "RUN_CHANGED"])
def test_a_run_that_cannot_do_what_was_asked_exits_1_with_one_line(
    code: str, capsys: pytest.CaptureFixture[str]
) -> None:
    failure = ApplicationError(code, "run 'run-1' is already completed")
    assert cli(Resumer(failure)).run(resume_args()) == 1
    assert cli(canceller=Canceller(failure)).run(cancel_args()) == 1
    assert capsys.readouterr().err.count("error: run 'run-1' is already completed") == 2


@pytest.mark.parametrize("code", ["SECRET_MISSING", "DATABASE_UNAVAILABLE", "SCHEMA_OUT_OF_DATE"])
def test_setup_trouble_exits_2(code: str, capsys: pytest.CaptureFixture[str]) -> None:
    failure = ApplicationError(code, "the stack is not ready")
    assert cli(Resumer(failure)).run(resume_args()) == 2
    assert "error: the stack is not ready" in capsys.readouterr().err


def test_a_missing_runtime_extra_says_how_to_install_it(capsys: pytest.CaptureFixture[str]) -> None:
    def missing() -> ResumeRunInterface:
        raise ImportError("no alembic", name="alembic")

    assert RunCli(missing, lambda: Canceller(), lambda: Reader()).run(resume_args()) == 1
    err = capsys.readouterr().err
    assert "pip install 'engineering-influence[runtime]'" in err
    assert "alembic is missing" in err


def test_an_unexpected_failure_is_one_line_without_a_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure = ConnectionError("amqp://ei:hunter2@rabbitmq refused")
    assert cli(Resumer(failure)).run(resume_args()) == 2
    err = capsys.readouterr().err
    assert err.strip() == "error: ConnectionError while talking to the stack; run the command again"
    assert "hunter2" not in err


class FlakyQueue(QueueInterface):
    """Refuses the first job, as a broker that is briefly down, then accepts."""

    def __init__(self) -> None:
        self.refusals = 1
        self.jobs: list[tuple[str, dict[str, object]]] = []

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        if self.refusals:
            self.refusals -= 1
            raise ConnectionError("broker down")
        self.jobs.append((kind, payload))
        return "job-1"


def seeded(url: str, status: RunStatus) -> SqlModelRunRepository:
    runs = SqlModelRunRepository(url)
    runs.save(a_run(status))
    return runs


def test_the_real_command_resumes_a_parked_run_on_the_database(
    database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    runs = seeded(database_url, RunStatus.PARKED_CAPACITY)
    queue = InMemoryQueue()

    assert CliRuntime(queue=queue).build().run(["run", "resume", "run-1"]) == 0

    stored = runs.get("run-1")
    assert stored is not None and stored.status is RunStatus.RUNNING
    assert queue.jobs == [("run.advance", {"run_id": "run-1", "stage": "outline", "attempt": 1})]
    assert "is running at stage 'outline'" in capsys.readouterr().out
    runs.close()


def test_the_real_command_cancels_a_run_without_needing_the_broker(
    database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    monkeypatch.delenv("EI_RABBITMQ_URL", raising=False)
    runs = seeded(database_url, RunStatus.RUNNING)

    assert CliRuntime().build().run(["run", "cancel", "run-1"]) == 0

    stored = runs.get("run-1")
    assert stored is not None and stored.status is RunStatus.CANCELLED
    assert capsys.readouterr().out.strip() == "run run-1 is cancelled"
    runs.close()


def test_running_resume_again_after_the_broker_was_down_queues_the_stage(
    database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    runs = seeded(database_url, RunStatus.PARKED_CAPACITY)
    queue = FlakyQueue()
    runtime = CliRuntime(queue=queue)

    assert runtime.build().run(["run", "resume", "run-1"]) == 2
    assert "ConnectionError" in capsys.readouterr().err
    stored = runs.get("run-1")
    assert stored is not None and stored.status is RunStatus.RUNNING  # un-parked, not queued
    assert queue.jobs == []

    assert runtime.build().run(["run", "resume", "run-1"]) == 0
    assert [job[1]["stage"] for job in queue.jobs] == ["outline"]
    runs.close()


def test_the_real_command_refuses_an_unknown_run(
    database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    assert CliRuntime().build().run(["run", "cancel", "nope"]) == 1
    assert "no run 'nope'" in capsys.readouterr().err


def test_the_real_command_stops_on_a_database_that_was_never_migrated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", f"sqlite:///{tmp_path / 'fresh.db'}")
    assert CliRuntime().build().run(["run", "cancel", "run-1"]) == 2
    assert "ei db upgrade" in capsys.readouterr().err


def test_resuming_without_a_broker_url_stops_with_a_clear_message(
    database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    monkeypatch.delenv("EI_RABBITMQ_URL", raising=False)
    assert CliRuntime().build().run(["run", "resume", "run-1"]) == 2
    assert "EI_RABBITMQ_URL is not configured" in capsys.readouterr().err


def test_the_run_group_needs_a_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        CliRuntime().build().run(["run"])
    assert raised.value.code == 2
    assert "required" in capsys.readouterr().err


def test_status_prints_the_run_as_one_line_of_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli().run(status_args()) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    document = json.loads(out)
    assert (document["run_id"], document["status"], document["stage"]) == (
        "run-1",
        "running",
        "outline",
    )
    assert document["artifacts"] == ["brief.md"]
    assert document["budget"]["cap_micro_usd"] == 1_000


def test_status_of_an_unknown_run_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    failure = ApplicationError("RUN_NOT_FOUND", "no run 'run-1'", http_status=404)
    assert cli(reader=Reader(failure)).run(status_args()) == 1
    captured = capsys.readouterr()
    assert (captured.out, captured.err.strip()) == ("", "error: no run 'run-1'")


def test_the_real_status_command_reports_the_run_and_its_artifacts(
    database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    monkeypatch.delenv("EI_RABBITMQ_URL", raising=False)
    runs = seeded(database_url, RunStatus.PARKED_CAPACITY)
    artifacts = SqlModelArtifactStore(database_url)
    artifacts.put("run-1", "brief.md", b"# Brief")

    assert CliRuntime().build().run(["run", "status", "run-1"]) == 0

    document = json.loads(capsys.readouterr().out)
    assert (document["status"], document["stage"]) == ("parked_capacity", "outline")
    assert document["artifacts"] == ["brief.md"]
    artifacts.close()
    runs.close()


def test_the_real_status_command_refuses_an_unknown_run(
    database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    assert CliRuntime().build().run(["run", "status", "nope"]) == 1
    assert "no run 'nope'" in capsys.readouterr().err


def test_the_real_status_command_stops_on_a_database_that_was_never_migrated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", f"sqlite:///{tmp_path / 'fresh.db'}")
    assert CliRuntime().build().run(["run", "status", "run-1"]) == 2
    assert "ei db upgrade" in capsys.readouterr().err
