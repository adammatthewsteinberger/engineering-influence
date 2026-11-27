# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A title file given to a screenplay run is kept in it before the run is saved; any other kind of run refuses it."""

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
from engineering_influence.services.screenplay_title_parser import ScreenplayTitleParser

SCREENPLAY = BookBrief(BookKind.SCREENPLAY, "a film", 1_000_000)
SOURCE = SourceEntry(1, "Ada sails.", "0" * 64)
TITLE = 'source = "Book One"\n'


def test_the_title_file_is_kept_under_its_artifact_name() -> None:
    store, runs = InMemoryArtifactStore(), InMemoryRunRepository()
    creator = CreateRun(runs, InMemoryQueue(), artifacts=store)
    run = creator.create(SCREENPLAY, (SOURCE,), title=TITLE)
    assert store.get(run.run_id, ScreenplayTitleParser.ARTIFACT) == TITLE.encode("utf-8")


def test_a_title_file_is_refused_for_a_book_that_is_not_a_screenplay_and_no_run_is_saved() -> None:
    runs = InMemoryRunRepository()
    plan = StagePlan(BookKind.NONFICTION, ("brief", "build"))
    creator = CreateRun(
        runs, InMemoryQueue(), {BookKind.NONFICTION: plan}, artifacts=InMemoryArtifactStore()
    )
    with pytest.raises(ApplicationError) as refused:
        creator.create(BookBrief(BookKind.NONFICTION, "bees", 1_000_000), title=TITLE)
    assert refused.value.code == "RUN_KIND_UNSUPPORTED"
    assert list(runs.run_ids()) == []


def test_a_title_file_is_refused_by_a_build_that_cannot_keep_it() -> None:
    creator = CreateRun(InMemoryRunRepository(), InMemoryQueue())
    with pytest.raises(ApplicationError) as refused:
        creator.create(SCREENPLAY, (SOURCE,), title=TITLE)
    assert refused.value.code == "SOURCES_NOT_STORED"
