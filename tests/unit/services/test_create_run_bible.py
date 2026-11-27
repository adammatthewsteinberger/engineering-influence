# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A bible given to a screenplay run is kept in it before the run is saved; any other kind of run refuses it."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.models.bible_card import BibleCard
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.source_entry import SourceEntry
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.create_run import CreateRun

SCREENPLAY = BookBrief(BookKind.SCREENPLAY, "a film", 1_000_000)
CARD = BibleCard("character", "ada", {"name": "Ada"}, "Keeps the log.")
SOURCE = SourceEntry(1, "Ada sails.", "0" * 64)


def test_each_card_is_kept_under_its_bible_artifact_name() -> None:
    store, runs = InMemoryArtifactStore(), InMemoryRunRepository()
    creator = CreateRun(runs, InMemoryQueue(), artifacts=store)
    run = creator.create(SCREENPLAY, (SOURCE,), bible=(CARD,))
    assert "bible/character/ada.json" in store.names(run.run_id)
    assert (
        BibleCard.decode(store.get(run.run_id, "bible/character/ada.json").decode("utf-8")) == CARD
    )


def test_a_bible_is_refused_for_a_book_that_is_not_a_screenplay_and_no_run_is_saved() -> None:
    runs = InMemoryRunRepository()
    plan = StagePlan(BookKind.NONFICTION, ("brief", "build"))
    creator = CreateRun(
        runs, InMemoryQueue(), {BookKind.NONFICTION: plan}, artifacts=InMemoryArtifactStore()
    )
    with pytest.raises(ApplicationError) as refused:
        creator.create(BookBrief(BookKind.NONFICTION, "bees", 1_000_000), bible=(CARD,))
    assert refused.value.code == "BIBLE_KIND_UNSUPPORTED"
    assert list(runs.run_ids()) == []


def test_a_bible_is_refused_by_a_build_that_cannot_keep_it() -> None:
    runs = InMemoryRunRepository()
    creator = CreateRun(runs, InMemoryQueue())
    with pytest.raises(ApplicationError) as refused:
        creator.create(SCREENPLAY, (SOURCE,), bible=(CARD,))
    assert refused.value.code == "SOURCES_NOT_STORED"
    assert list(runs.run_ids()) == []
