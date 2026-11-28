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
from engineering_influence.models.export_summary import ExportSummary
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.runtime.cli_runtime import CliRuntime
from engineering_influence.services.brief_reader import BriefReader
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface
from engineering_influence.services.interfaces.export_run_interface import ExportRunInterface
from engineering_influence.services.interfaces.list_runs_interface import ListRunsInterface
from engineering_influence.services.interfaces.resolve_spend_consent_interface import (
    ResolveSpendConsentInterface,
)
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


class Exporter(ExportRunInterface):
    def __init__(self, failure: BaseException | None = None) -> None:
        self.failure = failure
        self.seen: list[tuple[str, Path]] = []

    def export(self, run_id: str, target: Path) -> ExportSummary:
        if self.failure is not None:
            raise self.failure
        self.seen.append((run_id, target))
        return ExportSummary(5, 3)


class Reader(RunControllerInterface):
    def __init__(self, failure: BaseException | None = None) -> None:
        self.failure = failure

    def summary(self, run_id: str) -> RunSummaryV1:
        if self.failure is not None:
            raise self.failure
        return RunSummaryV1.from_run(a_run(RunStatus.RUNNING), ["brief.md"])

    def artifact(self, run_id: str, name: str) -> bytes:
        raise NotImplementedError


class Creator(CreateRunInterface):
    def __init__(self, failure: BaseException | None = None) -> None:
        self.failure = failure
        self.briefs: list[BookBrief] = []

    def create(self, brief: BookBrief, servers: tuple[str, ...] | None = None) -> BookRun:
        if self.failure is not None:
            raise self.failure
        self.briefs.append(brief)
        plan = StagePlan(kind=brief.kind, stages=("brief", "outline"))
        return BookRun("run-1", brief, plan, Budget(cap=brief.budget_micro_usd))


class Lister(ListRunsInterface):
    def __init__(self, runs: tuple[BookRun, ...] = ()) -> None:
        self._runs = runs

    def runs(self) -> tuple[BookRun, ...]:
        return self._runs


class Resolver(ResolveSpendConsentInterface):
    def __init__(self, failure: BaseException | None = None) -> None:
        self.failure = failure
        self.seen: list[tuple[str, str, int | None]] = []

    def grant(self, run_id: str, micro_usd: int | None = None) -> BookRun:
        if self.failure is not None:
            raise self.failure
        self.seen.append(("grant", run_id, micro_usd))
        return a_run(RunStatus.RUNNING)

    def deny(self, run_id: str) -> BookRun:
        if self.failure is not None:
            raise self.failure
        self.seen.append(("deny", run_id, None))
        return a_run(RunStatus.PARKED_CAPACITY)


def cli(
    resumer: Resumer | None = None,
    canceller: Canceller | None = None,
    reader: Reader | None = None,
    exporter: Exporter | None = None,
    creator: Creator | None = None,
    lister: Lister | None = None,
    resolver: Resolver | None = None,
) -> RunCli:
    return RunCli(
        lambda: resumer or Resumer(),
        lambda: canceller or Canceller(),
        lambda: reader or Reader(),
        lambda: exporter or Exporter(),
        lambda: creator or Creator(),
        lambda: lister or Lister(),
        BriefReader(),
        lambda: resolver or Resolver(),
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


def export_args(directory: str = "out") -> argparse.Namespace:
    return argparse.Namespace(run_command="export", run_id="run-1", directory=Path(directory))


def test_exporting_writes_to_the_folder_and_says_what_is_where(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exporter = Exporter()
    assert cli(exporter=exporter).run(export_args("my-book")) == 0
    assert exporter.seen == [("run-1", Path("my-book"))]
    assert capsys.readouterr().out.strip() == (
        "exported 5 files of run run-1 to my-book: 3 are the book (books/ and src/), "
        "the rest are under run/"
    )


@pytest.mark.parametrize(
    "code", ["RUN_NOT_FOUND", "RUN_HAS_NO_ARTIFACTS", "EXPORT_TARGET_NOT_EMPTY"]
)
def test_an_export_that_cannot_be_done_exits_1_with_one_line(
    code: str, capsys: pytest.CaptureFixture[str]
) -> None:
    failure = ApplicationError(code, "nothing to do here")
    assert cli(exporter=Exporter(failure)).run(export_args()) == 1
    assert capsys.readouterr().err.strip() == "error: nothing to do here"


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

    assert (
        RunCli(
            missing,
            lambda: Canceller(),
            lambda: Reader(),
            lambda: Exporter(),
            lambda: Creator(),
            lambda: Lister(),
            BriefReader(),
            lambda: Resolver(),
        ).run(resume_args())
        == 1
    )
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


def test_the_real_command_exports_a_runs_book_and_outputs_to_a_new_folder(
    database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    runs = seeded(database_url, RunStatus.RUNNING)
    artifacts = SqlModelArtifactStore(database_url)
    artifacts.put("run-1", "brief.md", b"the brief")
    artifacts.put("run-1", "manuscript/books/hive.toml", b"title = 'x'")
    artifacts.put("run-1", "manuscript/src/chapter_01.md", b"# One\n")
    target = tmp_path / "my-book"

    assert CliRuntime().build().run(["run", "export", "run-1", str(target)]) == 0

    assert (target / "books" / "hive.toml").read_bytes() == b"title = 'x'"
    assert (target / "src" / "chapter_01.md").read_bytes() == b"# One\n"
    assert (target / "run" / "brief.md").read_bytes() == b"the brief"
    assert "exported 3 files of run run-1" in capsys.readouterr().out
    assert CliRuntime().build().run(["run", "export", "run-1", str(target)]) == 1
    assert "not an empty folder" in capsys.readouterr().err
    runs.close()
    artifacts.close()


def test_the_real_export_of_an_unknown_run_exits_1_and_creates_nothing(
    database_url: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    target = tmp_path / "my-book"
    assert CliRuntime().build().run(["run", "export", "nope", str(target)]) == 1
    assert "no run 'nope'" in capsys.readouterr().err
    assert not target.exists()


def write_brief(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "brief.toml"
    path.write_text(text, encoding="utf-8")
    return path


GOOD_BRIEF = 'kind = "nonfiction"\nidea = "sourdough at home"\nbudget_micro_usd = 5000000\n'


def test_a_brief_file_starts_a_run_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    creator = Creator()
    args = argparse.Namespace(run_command="create", brief=write_brief(tmp_path, GOOD_BRIEF))
    assert cli(creator=creator).run(args) == 0
    (brief,) = creator.briefs
    assert (brief.kind, brief.idea, brief.budget_micro_usd) == (
        BookKind.NONFICTION,
        "sourdough at home",
        5_000_000,
    )
    assert (
        capsys.readouterr().out
        == "run run-1 is pending at stage 'brief'; its first stage is queued\n"
    )


def test_a_brief_that_is_not_toml_is_refused_on_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = argparse.Namespace(run_command="create", brief=write_brief(tmp_path, "kind = "))
    assert cli().run(args) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "is not valid TOML" in err and err.count("\n") == 1


def test_a_brief_the_contract_refuses_names_the_problem(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = GOOD_BRIEF.replace("sourdough at home", "   ")
    args = argparse.Namespace(run_command="create", brief=write_brief(tmp_path, text))
    assert cli().run(args) == 1
    err = capsys.readouterr().err
    assert "is not a brief: idea" in err and err.count("\n") == 1


def test_a_brief_with_an_unknown_key_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = argparse.Namespace(
        run_command="create", brief=write_brief(tmp_path, GOOD_BRIEF + "mood = 'grim'\n")
    )
    assert cli().run(args) == 1
    assert "is not a brief:" in capsys.readouterr().err


def test_a_missing_brief_file_is_refused_on_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = argparse.Namespace(run_command="create", brief=tmp_path / "absent.toml")
    assert cli().run(args) == 1
    assert "cannot read" in capsys.readouterr().err


def test_a_run_refused_for_its_kind_exits_one_with_the_reason(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    refused = ApplicationError(
        code="RUN_KIND_UNSUPPORTED", message="this build cannot start a novel book", http_status=422
    )
    args = argparse.Namespace(run_command="create", brief=write_brief(tmp_path, GOOD_BRIEF))
    assert cli(creator=Creator(refused)).run(args) == 1
    assert capsys.readouterr().err == "error: this build cannot start a novel book\n"


def test_runs_lists_one_line_each_with_status_and_stage(capsys: pytest.CaptureFixture[str]) -> None:
    runs = (a_run(RunStatus.RUNNING), a_run(RunStatus.PARKED_CAPACITY))
    assert cli(lister=Lister(runs)).run(argparse.Namespace(run_command="runs")) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "run-1  " + f"{'running':<18} outline"
    assert [line.split()[1:] for line in lines] == [
        ["running", "outline"],
        ["parked_capacity", "outline"],
    ]


def test_runs_with_nothing_saved_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli().run(argparse.Namespace(run_command="runs")) == 0
    assert capsys.readouterr().out == ""


def test_the_real_command_creates_a_run_on_the_database_and_queues_its_first_stage(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    queue = InMemoryQueue()
    brief = write_brief(tmp_path, GOOD_BRIEF)

    assert CliRuntime(queue=queue).build().run(["run", "create", str(brief)]) == 0

    (kind, payload) = queue.jobs[0]
    assert kind == "run.advance" and payload["stage"] == "brief" and payload["attempt"] == 1
    stored = SqlModelRunRepository(database_url).get(str(payload["run_id"]))
    assert stored is not None and stored.status is RunStatus.PENDING
    assert stored.budget.cap == 5_000_000
    assert "is pending at stage 'brief'" in capsys.readouterr().out


def test_the_real_command_lists_the_saved_runs_from_the_database(
    database_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EI_DATABASE_URL", database_url)
    seeded(database_url, RunStatus.PARKED_CAPACITY)

    assert CliRuntime().build().run(["run", "runs"]) == 0
    assert capsys.readouterr().out.split() == ["run-1", "parked_capacity", "outline"]


def test_grant_queues_the_run_and_reports_its_new_cap(capsys: pytest.CaptureFixture[str]) -> None:
    resolver = Resolver()
    args = argparse.Namespace(run_command="grant", run_id="run-1", micro_usd=None)
    assert cli(resolver=resolver).run(args) == 0
    assert resolver.seen == [("grant", "run-1", None)]
    assert "is running with a cap of 1000 micro-USD; its stage is queued" in capsys.readouterr().out


def test_grant_passes_the_amount_a_parked_run_continues_with() -> None:
    resolver = Resolver()
    args = argparse.Namespace(run_command="grant", run_id="run-1", micro_usd=500)
    assert cli(resolver=resolver).run(args) == 0
    assert resolver.seen == [("grant", "run-1", 500)]


def test_deny_parks_the_run_and_says_how_to_continue(capsys: pytest.CaptureFixture[str]) -> None:
    resolver = Resolver()
    assert cli(resolver=resolver).run(argparse.Namespace(run_command="deny", run_id="run-1")) == 0
    assert resolver.seen == [("deny", "run-1", None)]
    assert "is parked_capacity; grant it more budget to continue" in capsys.readouterr().out


def test_a_refused_grant_is_one_line_and_exit_one(capsys: pytest.CaptureFixture[str]) -> None:
    failure = ApplicationError(
        code="CONSENT_NOT_PENDING",
        message="run 'run-1' is not waiting for consent",
        http_status=409,
    )
    args = argparse.Namespace(run_command="grant", run_id="run-1", micro_usd=None)
    assert cli(resolver=Resolver(failure)).run(args) == 1
    assert "is not waiting for consent" in capsys.readouterr().err


def test_runs_says_how_much_a_run_waiting_for_consent_needs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    waiting = a_run(RunStatus.RUNNING).await_consent(SpendRequest(700, "outline"))
    assert cli(lister=Lister((waiting,))).run(argparse.Namespace(run_command="runs")) == 0
    out = capsys.readouterr().out
    assert "awaiting_consent" in out and "needs 700 micro-USD more" in out
