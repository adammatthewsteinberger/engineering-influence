# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Source files given to a new run are kept in it before it is saved; a build that cannot keep them refuses."""

import hashlib

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.source_entry import SourceEntry
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.create_run import CreateRun

PLAN = StagePlan(BookKind.NONFICTION, ("brief", "build"))
BRIEF = BookBrief(BookKind.NONFICTION, "bees", 1_000_000)


def entry(number: int, text: str) -> SourceEntry:
    return SourceEntry(number, text, hashlib.sha256(text.encode("utf-8")).hexdigest())


def test_each_source_is_kept_in_the_run_under_its_number() -> None:
    store, runs = InMemoryArtifactStore(), InMemoryRunRepository()
    creator = CreateRun(runs, InMemoryQueue(), {BookKind.NONFICTION: PLAN}, artifacts=store)
    run = creator.create(BRIEF, (entry(1, "one"), entry(2, "two")))
    assert store.names(run.run_id) == ["source/001.md", "source/002.md"]
    assert store.get(run.run_id, "source/002.md") == b"two"


def test_a_run_with_no_sources_keeps_no_artifacts() -> None:
    store, runs = InMemoryArtifactStore(), InMemoryRunRepository()
    creator = CreateRun(runs, InMemoryQueue(), {BookKind.NONFICTION: PLAN}, artifacts=store)
    run = creator.create(BRIEF)
    assert store.names(run.run_id) == []


def test_sources_are_refused_by_a_build_that_cannot_keep_them_and_no_run_is_saved() -> None:
    runs = InMemoryRunRepository()
    creator = CreateRun(runs, InMemoryQueue(), {BookKind.NONFICTION: PLAN})
    with pytest.raises(ApplicationError) as refused:
        creator.create(BRIEF, (entry(1, "one"),))
    assert refused.value.code == "SOURCES_NOT_STORED"
    assert list(runs.run_ids()) == []
