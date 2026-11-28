"""The maker describes a run's outcome; a run that stops or fails is a book that did not finish, never an exception."""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from smoke_rehearsal import NoSecrets, RehearsalBuilder, environment, serve

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.book_maker_interface import BookMakerInterface
from engineering_influence.interfaces.local_book_creator_interface import (
    LocalBookCreatorInterface,
)
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.evaluation_case import EvaluationCase
from engineering_influence.models.run_status import RunStatus
from engineering_influence.runtime.local_book_maker import LocalBookMaker

TODAY = date(2026, 11, 22)
CASE = EvaluationCase(
    "herbs", BookKind.NONFICTION, "How to keep herbs alive indoors", "Herbs Indoors", 400
)


def maker(tmp_path: Path, url: str) -> LocalBookMaker:
    return LocalBookMaker(
        tmp_path / "work", environment(tmp_path, url), NoSecrets(), TODAY, RehearsalBuilder()
    )


def test_a_finished_book_is_described_by_what_the_run_wrote(tmp_path: Path) -> None:
    with serve() as server:
        book = maker(tmp_path, server.url).make(CASE, 5_000_000)
    assert isinstance(maker(tmp_path, "http://127.0.0.1:1"), BookMakerInterface)
    assert (book.case, book.kind, book.run_status, book.finished) == (
        "herbs",
        BookKind.NONFICTION,
        "completed",
        True,
    )
    assert book.title == "Herbs Indoors" and len(book.chapters) == 3
    assert book.chapters[0].startswith("# Light") and "bright window" in book.chapters[0]
    assert 0 < book.spent_micro_usd <= 5_000_000
    assert isinstance(book.estimated_micro_usd, int) and book.estimated_micro_usd > 0


def test_a_run_that_stops_for_money_it_was_not_given_is_a_book_that_did_not_finish(
    tmp_path: Path,
) -> None:
    with serve() as server:
        book = maker(tmp_path, server.url).make(CASE, 1_000)
    assert book.finished is False and book.run_status != "completed"
    assert book.chapters == () and book.title == "Herbs Indoors"
    assert not (tmp_path / "work" / "herbs").exists()


def test_a_run_that_fails_before_it_stores_anything_is_described_not_raised(
    tmp_path: Path,
) -> None:
    with serve(failures={"Write the brief": 99}) as server:
        book = maker(tmp_path, server.url).make(CASE, 5_000_000)
    assert (book.run_status, book.finished, book.chapters) == ("failed", False, ())


def test_an_export_error_other_than_nothing_stored_is_not_hidden() -> None:
    class Creator:
        def export(self, directory: Path) -> None:
            raise ApplicationError(code="DISK_FULL", message="no space", http_status=507)

    with pytest.raises(ApplicationError) as error:
        LocalBookMaker._export(Creator(), Path("x"))  # type: ignore[arg-type]
    assert error.value.code == "DISK_FULL"


def test_the_quality_report_is_read_only_when_it_is_an_object(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    assert LocalBookMaker._quality(tmp_path) == {}
    (run / "quality-report.json").write_text(json.dumps(["not", "an", "object"]))
    assert LocalBookMaker._quality(tmp_path) == {}
    (run / "quality-report.json").write_text(json.dumps({"status": "pass"}))
    assert LocalBookMaker._quality(tmp_path) == {"status": "pass"}


@pytest.mark.parametrize(
    ("toml", "expected"),
    [
        ('title = "From The Config"\n', "From The Config"),
        ('title = "   "\n', "Herbs Indoors"),
        ("pages = 3\n", "Herbs Indoors"),
        (None, "Herbs Indoors"),
    ],
)
def test_the_title_is_the_books_own_then_the_cases_hint_then_its_name(
    tmp_path: Path, toml: str | None, expected: str
) -> None:
    if toml is not None:
        (tmp_path / "books").mkdir()
        (tmp_path / "books" / "a.toml").write_text(toml)
    assert LocalBookMaker._title(tmp_path, CASE) == expected
    bare = EvaluationCase("herbs", BookKind.NONFICTION, "idea")
    assert LocalBookMaker._title(tmp_path, bare) == (
        expected if toml and "From" in toml else "herbs"
    )


def test_what_a_failed_run_did_write_is_still_exported_for_reading(tmp_path: Path) -> None:
    with serve(failures={"Summarise this chapter": 99}) as server:
        book = maker(tmp_path, server.url).make(CASE, 5_000_000)
    assert (book.run_status, book.finished, book.chapters) == ("failed", False, ())
    assert "retries-exhausted" in book.issues[0]
    assert (tmp_path / "work" / "herbs" / "run" / "chapter_01.md").is_file()


class FakeCreator:
    """Stands in for the runtime: reports a chosen status and writes a chosen quality verdict and chapters."""

    def __init__(
        self, status: RunStatus, verdict: str | None, chapters: int, fail_start: bool = False
    ) -> None:
        self.status = status
        self.verdict = verdict
        self.chapters = chapters
        self.fail_start = fail_start
        self.closed = 0

    def start(self, brief: object, progress: object, sources: object = ()) -> SimpleNamespace:
        if self.fail_start:
            raise ApplicationError(code="BOOM", message="stopped", http_status=500)
        return SimpleNamespace(status=self.status, budget=SimpleNamespace(spent=7), issues=())

    def export(self, directory: Path) -> None:
        (directory / "src").mkdir(parents=True)
        (directory / "run").mkdir()
        for number in range(1, self.chapters + 1):
            (directory / "src" / f"chapter_{number:02d}.md").write_text(f"# Chapter {number}\n")
        if self.verdict is not None:
            report = {"status": self.verdict}
            (directory / "run" / "quality-report.json").write_text(json.dumps(report))

    def close(self) -> None:
        self.closed += 1


class FakeMaker(LocalBookMaker):
    def __init__(self, tmp_path: Path, creator: FakeCreator) -> None:
        super().__init__(tmp_path / "work", {}, NoSecrets(), TODAY)
        self.fake = creator

    def _creator(self, case: EvaluationCase) -> LocalBookCreatorInterface:
        return self.fake  # type: ignore[return-value]


@pytest.mark.parametrize(
    ("status", "verdict", "chapters", "finished"),
    [
        (RunStatus.COMPLETED, "pass", 2, True),
        (RunStatus.COMPLETED, "fail", 2, False),
        (RunStatus.COMPLETED, None, 2, False),
        (RunStatus.COMPLETED, "pass", 0, False),
        (RunStatus.FAILED, "pass", 2, False),
    ],
)
def test_a_book_is_finished_only_when_the_run_completed_the_quality_report_passed_and_chapters_exist(
    tmp_path: Path, status: RunStatus, verdict: str | None, chapters: int, finished: bool
) -> None:
    book = FakeMaker(tmp_path, FakeCreator(status, verdict, chapters)).make(CASE, 1)
    assert book.finished is finished
    assert (book.run_status, len(book.chapters), book.spent_micro_usd) == (
        status.value,
        chapters,
        7,
    )


def test_the_runtime_is_closed_after_a_case_whether_or_not_it_finished(tmp_path: Path) -> None:
    done = FakeCreator(RunStatus.COMPLETED, "pass", 1)
    FakeMaker(tmp_path, done).make(CASE, 1)
    assert done.closed == 1
    broken = FakeCreator(RunStatus.COMPLETED, "pass", 1, fail_start=True)
    with pytest.raises(ApplicationError):
        FakeMaker(tmp_path, broken).make(CASE, 1)
    assert broken.closed == 1
