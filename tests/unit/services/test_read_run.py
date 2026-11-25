"""Reading a run and its artifacts: the service and the controller over it."""

import pytest

from engineering_influence.controllers.run_controller import RunController
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.read_run import ReadRun


def seeded() -> tuple[InMemoryRunRepository, InMemoryArtifactStore]:
    brief = BookBrief(kind=BookKind.NONFICTION, idea="sourdough", budget_micro_usd=1_000)
    plan = StagePlan(kind=BookKind.NONFICTION, stages=("brief", "outline"))
    runs, artifacts = InMemoryRunRepository(), InMemoryArtifactStore()
    runs.save(BookRun("run-1", brief, plan, Budget(cap=1_000), status=RunStatus.RUNNING))
    artifacts.put("run-1", "outline.md", b"two")
    artifacts.put("run-1", "brief.md", b"one")
    artifacts.put("run-2", "other.md", b"not ours")
    return runs, artifacts


def test_the_summary_is_the_run_and_the_names_of_its_artifacts_only() -> None:
    runs, artifacts = seeded()
    run, names = ReadRun(runs, artifacts).summary("run-1")
    assert run.run_id == "run-1"
    assert names == ["brief.md", "outline.md"]


def test_a_run_that_does_not_exist_is_a_404() -> None:
    runs, artifacts = seeded()
    with pytest.raises(ApplicationError) as raised:
        ReadRun(runs, artifacts).summary("nope")
    assert (raised.value.code, raised.value.http_status) == ("RUN_NOT_FOUND", 404)


def test_an_artifact_comes_back_byte_for_byte() -> None:
    runs, artifacts = seeded()
    data = bytes(range(256))
    artifacts.put("run-1", "book.epub", data)
    assert ReadRun(runs, artifacts).artifact("run-1", "book.epub") == data


@pytest.mark.parametrize(
    ("run_id", "name"),
    [
        ("run-1", "missing.md"),
        ("run-9", "brief.md"),
        ("run-1", "../run-2/other.md"),
        ("run-1", "/etc/passwd"),
        ("run-1", "a\\b.md"),
        ("run-1", ""),
        ("..", "x"),
    ],
)
def test_a_missing_or_impossible_artifact_looks_the_same(run_id: str, name: str) -> None:
    runs, artifacts = seeded()
    with pytest.raises(ApplicationError) as raised:
        ReadRun(runs, artifacts).artifact(run_id, name)
    assert (raised.value.code, raised.value.http_status) == ("ARTIFACT_NOT_FOUND", 404)


def test_reading_changes_nothing() -> None:
    runs, artifacts = seeded()
    before = (runs.get("run-1"), artifacts.names("run-1"))
    reader = ReadRun(runs, artifacts)
    reader.summary("run-1")
    reader.artifact("run-1", "brief.md")
    assert (runs.get("run-1"), artifacts.names("run-1")) == before


def test_the_controller_turns_the_answer_into_the_versioned_contract() -> None:
    runs, artifacts = seeded()
    controller = RunController(ReadRun(runs, artifacts))
    summary = controller.summary("run-1")
    assert (summary.schema_version, summary.run_id, summary.status) == (
        1,
        "run-1",
        RunStatus.RUNNING,
    )
    assert summary.artifacts == ("brief.md", "outline.md")
    assert controller.artifact("run-1", "brief.md") == b"one"
