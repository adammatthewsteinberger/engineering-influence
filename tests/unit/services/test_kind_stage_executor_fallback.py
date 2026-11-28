# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""KindStageExecutor with a fallback: a kind it does not list goes to the fallback, and without one it is refused."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.kind_stage_executor import KindStageExecutor


class Named(StageExecutorInterface):
    def __init__(self, name: str) -> None:
        self.name = name

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        return StageReport()


def run(kind: BookKind) -> BookRun:
    brief = BookBrief(kind, "x", 1_000_000)
    return BookRun(
        run_id="run-1", brief=brief, plan=StagePlan(kind, ("audit",)), budget=Budget(cap=1_000_000)
    )


def test_a_listed_kind_uses_its_executor() -> None:
    chosen = Named("nonfiction")
    executor = KindStageExecutor({BookKind.NONFICTION: chosen}, fallback=Named("default"))
    assert asyncio.run(executor.execute(run(BookKind.NONFICTION), 1)) == StageReport()


def test_an_unlisted_kind_goes_to_the_fallback() -> None:
    used: list[str] = []

    class Recording(StageExecutorInterface):
        async def execute(self, run: BookRun, attempt: int) -> StageReport:
            used.append(run.brief.kind.value)
            return StageReport()

    executor = KindStageExecutor({BookKind.NONFICTION: Named("nonfiction")}, fallback=Recording())
    asyncio.run(executor.execute(run(BookKind.SCREENPLAY), 1))
    assert used == ["screenplay"]


def test_an_unlisted_kind_with_no_fallback_is_refused() -> None:
    with pytest.raises(ApplicationError) as refused:
        asyncio.run(
            KindStageExecutor({BookKind.NONFICTION: Named("n")}).execute(
                run(BookKind.SCREENPLAY), 1
            )
        )
    assert refused.value.code == "STAGE_KIND_UNSUPPORTED"
