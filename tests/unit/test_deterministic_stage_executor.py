"""The placeholder stage executor: offline, deterministic, and through the journal."""

import asyncio

from engineering_influence.infrastructure.deterministic_stage_executor import (
    DeterministicStageExecutor,
)
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_report import StageReport


def a_run(idea: str = "sourdough") -> BookRun:
    brief = BookBrief(kind=BookKind.NONFICTION, idea=idea, budget_micro_usd=1_000)
    plan = StagePlan(kind=BookKind.NONFICTION, stages=("brief", "outline"))
    return BookRun("run-1", brief, plan, Budget(cap=1_000))


def test_it_stores_the_stage_artifact_and_a_free_journal_entry() -> None:
    artifacts, journal = InMemoryArtifactStore(), InMemoryJournal()
    report = asyncio.run(DeterministicStageExecutor(artifacts, journal).execute(a_run(), 1))
    assert report == StageReport()
    assert artifacts.get("run-1", "brief.md") == b"brief: draft for sourdough"
    [entry] = journal.entries("run-1")
    assert (entry.stage, entry.attempt, entry.cost_micro_usd) == ("brief", 1, 0)
    assert entry.response == "brief: draft for sourdough"


def test_running_a_stage_twice_changes_nothing() -> None:
    artifacts, journal = InMemoryArtifactStore(), InMemoryJournal()
    executor = DeterministicStageExecutor(artifacts, journal)
    asyncio.run(executor.execute(a_run(), 1))
    asyncio.run(executor.execute(a_run(), 2))
    assert len(journal.entries("run-1")) == 1
    assert artifacts.names("run-1") == ["brief.md"]


def test_a_repeated_stage_replays_the_first_recorded_answer() -> None:
    artifacts, journal = InMemoryArtifactStore(), InMemoryJournal()
    executor = DeterministicStageExecutor(artifacts, journal)
    asyncio.run(executor.execute(a_run(), 1))
    # The journal already holds an answer for this request, so the artifact must match it.
    first = journal.entries("run-1")[0]
    other = JournalEntry("run-1", "brief", 2, first.key, "something else", 0)
    assert journal.record(other) == first
    asyncio.run(executor.execute(a_run(), 2))
    assert artifacts.get("run-1", "brief.md") == first.response.encode()
