# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A previous shooting script lock given to a new screenplay run is kept in it before it is saved; any other kind of run,
or a build that cannot keep it, is refused before anything is saved."""

import hashlib

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.source_entry import SourceEntry
from engineering_influence.services.create_run import CreateRun

LOCK = '{"version": 1, "entries": []}'
FILM = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000)
SOURCE = SourceEntry(1, "one", hashlib.sha256(b"one").hexdigest())


def test_the_lock_is_kept_in_the_screenplay_run_as_its_previous_lock() -> None:
    store, runs = InMemoryArtifactStore(), InMemoryRunRepository()
    run = CreateRun(runs, InMemoryQueue(), artifacts=store).create(FILM, (SOURCE,), LOCK)
    assert store.get(run.run_id, "previous_shooting_lock.json") == LOCK.encode("utf-8")


def test_a_run_without_a_lock_keeps_none() -> None:
    store, runs = InMemoryArtifactStore(), InMemoryRunRepository()
    run = CreateRun(runs, InMemoryQueue(), artifacts=store).create(FILM, (SOURCE,))
    assert store.get(run.run_id, "previous_shooting_lock.json") is None


def test_a_lock_for_another_kind_of_run_is_refused_before_anything_is_saved() -> None:
    runs = InMemoryRunRepository()
    creator = CreateRun(runs, InMemoryQueue(), artifacts=InMemoryArtifactStore())
    with pytest.raises(ApplicationError) as refused:
        creator.create(BookBrief(BookKind.NONFICTION, "bees", 1_000_000), (SOURCE,), LOCK)
    assert refused.value.code == "RUN_KIND_UNSUPPORTED"
    assert list(runs.run_ids()) == []


def test_a_lock_is_refused_by_a_build_that_cannot_keep_it() -> None:
    runs = InMemoryRunRepository()
    with pytest.raises(ApplicationError) as refused:
        CreateRun(runs, InMemoryQueue()).create(FILM, (SOURCE,), LOCK)
    assert refused.value.code == "SOURCES_NOT_STORED"
    assert list(runs.run_ids()) == []
