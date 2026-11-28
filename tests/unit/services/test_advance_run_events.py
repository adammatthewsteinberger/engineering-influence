# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""AdvanceRun queues the webhook events of its transitions with the change, and none when no receiver is configured."""

import asyncio

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.run_event_builder import RunEventBuilder


class Succeeds(StageExecutorInterface):
    """Every stage finishes with no issues."""

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        return StageReport()


def advance_run(runs: InMemoryRunRepository, urls: tuple[str, ...]) -> AdvanceRun:
    return AdvanceRun(
        runs,
        InMemoryJournal(),
        Succeeds(),
        InMemoryQueue(),
        FailureClassifier(),
        events=RunEventBuilder(urls),
    )


def a_pending_run() -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "bees", 5_000_000)
    return BookRun(
        run_id="run-1", brief=brief, plan=NonfictionRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def test_starting_and_finishing_a_stage_queues_its_events_with_the_change() -> None:
    runs = InMemoryRunRepository()
    runs.save(a_pending_run())
    outcome = asyncio.run(
        advance_run(runs, ("https://hook.example/in",)).advance("run-1", "brief", 1)
    )
    assert outcome is AdvanceOutcome.ADVANCED
    assert sorted(event.event_name for event in runs.queued()) == [
        "phase.completed",
        "pipeline.started",
    ]


def test_with_no_receiver_no_event_is_queued() -> None:
    runs = InMemoryRunRepository()
    runs.save(a_pending_run())
    asyncio.run(advance_run(runs, ()).advance("run-1", "brief", 1))
    assert runs.queued() == ()


class Breaks(StageExecutorInterface):
    """The first stage cannot run: its error is one the run cannot recover from."""

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        raise ApplicationError(code="STAGE_OUTPUT_INVALID", message="brief: bad", http_status=422)


def test_a_stage_that_cannot_run_queues_a_failure_event_with_its_code() -> None:
    runs = InMemoryRunRepository()
    runs.save(a_pending_run())
    advance = AdvanceRun(
        runs,
        InMemoryJournal(),
        Breaks(),
        InMemoryQueue(),
        FailureClassifier(),
        events=RunEventBuilder(("https://hook.example/in",)),
    )
    outcome = asyncio.run(advance.advance("run-1", "brief", 1))
    assert outcome is AdvanceOutcome.FAILED
    (failure,) = [event for event in runs.queued() if event.event_name == "pipeline.failed"]
    assert failure.payload["code"] == "stage-failed"
