# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""StageExecutorRouter: a stage with its own executor goes there, every other stage to the default."""

import asyncio

from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.stage_executor_router import StageExecutorRouter


class Recorder(StageExecutorInterface):
    def __init__(self, name: str) -> None:
        self.name = name
        self.seen: list[tuple[str, int]] = []

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        self.seen.append((run.stage, attempt))
        return StageReport((QualityIssue(run.stage, self.name, "ran", blocking=False),))


def run_at(stage: str) -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "bees", 1_000)
    return BookRun("run-1", brief, NonfictionRecipes().plan(), Budget(cap=1_000), stage=stage)


def route(stage: str, attempt: int = 1) -> tuple[StageReport, Recorder, Recorder]:
    default, special = Recorder("default"), Recorder("special")
    router = StageExecutorRouter(default, {"draft": special})
    assert isinstance(router, StageExecutorInterface)
    return asyncio.run(router.execute(run_at(stage), attempt)), default, special


def test_a_stage_with_its_own_executor_goes_there_with_its_attempt() -> None:
    report, default, special = route("draft", attempt=3)
    assert report.issues[0].code == "special"
    assert special.seen == [("draft", 3)]
    assert default.seen == []


def test_every_other_stage_goes_to_the_default() -> None:
    for stage in ("brief", "positioning", "research", "outline"):
        report, default, special = route(stage)
        assert report.issues[0].code == "default"
        assert default.seen == [(stage, 1)]
        assert special.seen == []


def test_the_map_is_copied_so_a_later_change_to_it_does_not_reroute() -> None:
    default, special = Recorder("default"), Recorder("special")
    mapping: dict[str, StageExecutorInterface] = {"draft": special}
    router = StageExecutorRouter(default, mapping)
    mapping.clear()
    asyncio.run(router.execute(run_at("draft"), 1))
    assert special.seen == [("draft", 1)]
