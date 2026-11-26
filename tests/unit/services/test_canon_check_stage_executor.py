# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""CanonCheckStageExecutor: with no check nothing happens; findings become issues; a blocking ERROR stops the run; a check
that cannot be read is refused."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.canon_check_interface import CanonCheckInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.services.canon_check_stage_executor import CanonCheckStageExecutor
from engineering_influence.services.canon_finding_parser import CanonFindingParser
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes


class FakeCheck(CanonCheckInterface):
    def __init__(self, status: int, output: str) -> None:
        self._status = status
        self._output = output

    def run(self) -> tuple[int, str]:
        return self._status, self._output


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000, title_hint="TEST FILM")
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def stage(check: CanonCheckInterface | None, blocking: bool) -> CanonCheckStageExecutor:
    return CanonCheckStageExecutor(check, CanonFindingParser(), blocking)


def test_with_no_check_configured_nothing_happens() -> None:
    report = asyncio.run(stage(None, True).execute(run(), 1))
    assert report.issues == ()


def test_each_finding_is_a_quality_issue_and_none_blocks_when_not_set_to() -> None:
    check = FakeCheck(1, "ERROR scene 12: [wrong-date] bad sol\nWARN scene 40: [tone] a lecture\n")
    report = asyncio.run(stage(check, False).execute(run(), 1))
    assert [issue.code for issue in report.issues] == ["canon-finding", "canon-finding"]
    assert report.issues[0].detail == "scene 12: [wrong-date] bad sol"
    assert all(not issue.blocking for issue in report.issues)


def test_a_blocking_error_stops_the_run_and_names_the_errors() -> None:
    check = FakeCheck(1, "ERROR scene 12: [wrong-date] bad sol\nWARN scene 40: [tone] a lecture\n")
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(check, True).execute(run(), 1))
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert "1 error(s): scene 12: [wrong-date] bad sol" in error.value.message


def test_warnings_alone_never_block() -> None:
    check = FakeCheck(0, "WARN scene 40: [tone] a lecture\n")
    report = asyncio.run(stage(check, True).execute(run(), 1))
    assert len(report.issues) == 1


def test_a_failed_check_with_nothing_readable_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(FakeCheck(2, "traceback: boom\n"), False).execute(run(), 1))
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert "status 2" in error.value.message
