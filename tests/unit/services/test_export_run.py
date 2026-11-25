# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ExportRun: the book at the top of the folder, everything else under run/, nothing overwritten."""

from collections.abc import Mapping
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.project_files_writer_interface import (
    ProjectFilesWriterInterface,
)
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.export_run import ExportRun
from engineering_influence.services.interfaces.export_run_interface import ExportRunInterface
from engineering_influence.services.interfaces.read_run_interface import ReadRunInterface


class Reader(ReadRunInterface):
    def __init__(self, artifacts: dict[str, bytes]) -> None:
        self.artifacts = artifacts

    def summary(self, run_id: str) -> tuple[BookRun, list[str]]:
        if run_id != "run-1":
            raise ApplicationError("RUN_NOT_FOUND", f"no run {run_id!r}", 404)
        brief = BookBrief(kind=BookKind.NONFICTION, idea="bees", budget_micro_usd=1_000)
        plan = StagePlan(kind=BookKind.NONFICTION, stages=("brief",))
        return BookRun("run-1", brief, plan, Budget(cap=1_000)), sorted(self.artifacts)

    def artifact(self, run_id: str, name: str) -> bytes:
        return self.artifacts[name]


class Writer(ProjectFilesWriterInterface):
    def __init__(self) -> None:
        self.calls: list[tuple[Path, dict[str, bytes]]] = []

    def write(self, root: Path, files: Mapping[str, bytes]) -> None:
        self.calls.append((root, dict(files)))


ARTIFACTS = {
    "brief.md": b"the brief",
    "audit/release-readiness.json": b"{}",
    "manuscript/books/hive.toml": b"title = 'x'",
    "manuscript/src/chapter_01.md": b"# One",
}


def exporter(artifacts: dict[str, bytes] | None = None) -> tuple[ExportRun, Writer]:
    writer = Writer()
    return ExportRun(Reader(ARTIFACTS if artifacts is None else artifacts), writer), writer


def test_it_is_an_export() -> None:
    assert isinstance(exporter()[0], ExportRunInterface)


def test_the_book_is_written_at_the_top_and_everything_else_under_run() -> None:
    export, writer = exporter()
    summary = export.export("run-1", Path("/out"))
    assert writer.calls == [
        (
            Path("/out"),
            {
                "run/audit/release-readiness.json": b"{}",
                "run/brief.md": b"the brief",
                "books/hive.toml": b"title = 'x'",
                "src/chapter_01.md": b"# One",
            },
        )
    ]
    assert (summary.files, summary.book_files) == (4, 2)


def test_a_run_that_has_not_assembled_yet_exports_what_it_has_with_no_book_files() -> None:
    export, writer = exporter({"brief.md": b"the brief"})
    summary = export.export("run-1", Path("/out"))
    assert writer.calls[0][1] == {"run/brief.md": b"the brief"}
    assert (summary.files, summary.book_files) == (1, 0)


def test_a_run_that_has_stored_nothing_is_refused_and_nothing_is_written() -> None:
    export, writer = exporter({})
    with pytest.raises(ApplicationError) as error:
        export.export("run-1", Path("/out"))
    assert (error.value.code, error.value.http_status) == ("RUN_HAS_NO_ARTIFACTS", 409)
    assert writer.calls == []


def test_an_unknown_run_is_refused_as_the_reader_says() -> None:
    export, writer = exporter()
    with pytest.raises(ApplicationError) as error:
        export.export("nope", Path("/out"))
    assert error.value.code == "RUN_NOT_FOUND" and writer.calls == []


def test_two_artifacts_that_would_land_on_one_path_are_refused() -> None:
    export, writer = exporter({"brief.md": b"a", "manuscript/run/brief.md": b"b"})
    with pytest.raises(ApplicationError) as error:
        export.export("run-1", Path("/out"))
    assert (error.value.code, error.value.http_status) == ("EXPORT_NAME_CLASH", 500)
    assert error.value.message == "two artifacts of run 'run-1' would be written to 'run/brief.md'"
    assert writer.calls == []
