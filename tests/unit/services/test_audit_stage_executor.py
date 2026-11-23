# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""AuditStageExecutor: the assembled book goes through the gates and the reports are kept either way."""

import asyncio
from collections.abc import Mapping

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.manuscript_auditor_interface import (
    ManuscriptAuditorInterface,
)
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.manuscript_audit import ManuscriptAudit
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.audit_stage_executor import AuditStageExecutor
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes

REPORTS = (("manuscript-audit.json", b"{audit}"), ("release-readiness.json", b"{release}"))


class Auditor(ManuscriptAuditorInterface):
    """Records what it was given and answers with a scripted audit."""

    def __init__(self, result: ManuscriptAudit) -> None:
        self.result = result
        self.calls: list[tuple[dict[str, bytes], str]] = []

    def audit(self, files: Mapping[str, bytes], slug: str) -> ManuscriptAudit:
        self.calls.append((dict(files), slug))
        return self.result


def passing(**changes: object) -> ManuscriptAudit:
    fields: dict[str, object] = {
        "passed": True,
        "status": "pass",
        "errors": (),
        "warnings": ("ebook-price-missing: no ebook price", "pricing-not-dated: no date"),
        "files": REPORTS,
    }
    return ManuscriptAudit(**{**fields, **changes})  # type: ignore[arg-type]


def failing() -> ManuscriptAudit:
    return ManuscriptAudit(
        passed=False,
        status="fail",
        errors=("forbidden-dash: page 3 has one", "missing-bio: no bio"),
        warnings=(),
        files=REPORTS,
    )


class World:
    def __init__(self, result: ManuscriptAudit, *, files: dict[str, bytes] | None = None) -> None:
        self.store = InMemoryArtifactStore()
        self.auditor = Auditor(result)
        self.executor = AuditStageExecutor(self.store, self.auditor)
        self.run = BookRun(
            run_id="run-1",
            brief=BookBrief(BookKind.NONFICTION, "bees", 1_000),
            plan=NonfictionRecipes().plan(),
            budget=Budget(cap=1_000),
            stage="audit",
        )
        default = {
            "manuscript/books/hive-mind.toml": b"title = 'x'",
            "manuscript/src/chapter_01.md": b"# One",
            "outline.md": b"not part of the manuscript",
        }
        for name, data in (default if files is None else files).items():
            self.store.put("run-1", name, data)

    def execute(self) -> StageReport:
        return asyncio.run(self.executor.execute(self.run, 1))

    def refused(self) -> ApplicationError:
        with pytest.raises(ApplicationError) as error:
            self.execute()
        return error.value

    def text(self, name: str) -> str:
        data = self.store.get("run-1", name)
        assert data is not None
        return data.decode("utf-8")


def test_it_is_a_stage_executor() -> None:
    assert isinstance(World(passing()).executor, StageExecutorInterface)
    assert AuditStageExecutor.STAGE == "audit"


def test_only_the_manuscript_files_are_given_as_a_project_with_the_books_slug() -> None:
    world = World(passing())
    assert world.execute() == StageReport()
    assert world.auditor.calls == [
        (
            {"books/hive-mind.toml": b"title = 'x'", "src/chapter_01.md": b"# One"},
            "hive-mind",
        )
    ]


def test_the_reports_are_stored_under_audit_with_a_summary() -> None:
    world = World(passing())
    world.execute()
    assert world.text("audit/manuscript-audit.json") == "{audit}"
    assert world.text("audit/release-readiness.json") == "{release}"
    assert world.text("audit.md") == (
        "# Audit\n\nStatus: pass\n\n"
        "## Errors\n\nNone.\n\n"
        "## Warnings\n\n- ebook-price-missing: no ebook price\n- pricing-not-dated: no date\n"
    )


def test_a_book_with_no_warnings_says_so() -> None:
    world = World(passing(warnings=()))
    world.execute()
    assert world.text("audit.md").endswith("## Warnings\n\nNone.\n")


def test_a_book_that_fails_is_refused_with_every_error_after_its_reports_are_kept() -> None:
    world = World(failing())
    error = world.refused()
    assert (error.code, error.http_status) == ("AUDIT_FAILED", 422)
    assert error.message == (
        "the assembled book 'hive-mind' did not pass its audit: "
        "forbidden-dash: page 3 has one; missing-bio: no bio"
    )
    assert world.text("audit/release-readiness.json") == "{release}"
    assert world.text("audit.md") == (
        "# Audit\n\nStatus: fail\n\n"
        "## Errors\n\n- forbidden-dash: page 3 has one\n- missing-bio: no bio\n\n"
        "## Warnings\n\nNone.\n"
    )


@pytest.mark.parametrize(
    "files",
    [
        {},
        {"outline.md": b"x"},
        {"manuscript/src/chapter_01.md": b"# One"},
        {"manuscript/books/a.toml": b"", "manuscript/books/b.toml": b""},
        {"manuscript/books/readme.md": b"not a config"},
    ],
)
def test_it_needs_exactly_one_book_config_from_the_assemble_stage(files: dict[str, bytes]) -> None:
    world = World(passing(), files=files)
    error = world.refused()
    assert (error.code, error.http_status) == ("STAGE_INPUT_MISSING", 409)
    assert "manuscript/books/" in error.message
    assert world.auditor.calls == []


def test_a_toml_file_outside_the_books_folder_is_not_taken_for_the_config() -> None:
    world = World(
        passing(),
        files={
            "manuscript/books/hive.toml": b"title = 'x'",
            "manuscript/src/notes.toml": b"not a config",
        },
    )
    world.execute()
    assert [slug for _, slug in world.auditor.calls] == ["hive"]
    assert sorted(world.auditor.calls[0][0]) == ["books/hive.toml", "src/notes.toml"]


def test_auditing_again_stores_the_same_reports_and_changes_nothing() -> None:
    world = World(passing())
    world.execute()
    before = {name: world.store.get("run-1", name) for name in world.store.names("run-1")}
    world.execute()
    assert {name: world.store.get("run-1", name) for name in world.store.names("run-1")} == before
