# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""An audiobook run has the outline and narration plan; any other mode, or an audiobook of a kind that is not nonfiction, is refused."""

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

BOOK = BookBrief(BookKind.NONFICTION, "a book", 1_000_000)
SOURCE = SourceEntry(1, "one", hashlib.sha256(b"one").hexdigest())


def test_an_audiobook_run_plans_the_outline_then_the_narration() -> None:
    creator = CreateRun(InMemoryRunRepository(), InMemoryQueue(), artifacts=InMemoryArtifactStore())
    run = creator.create(BOOK, (SOURCE,), None, None, "audiobook")
    assert tuple(run.plan.stages) == ("audiobook_outline", "narration")


def test_a_book_run_keeps_its_whole_plan() -> None:
    creator = CreateRun(InMemoryRunRepository(), InMemoryQueue(), artifacts=InMemoryArtifactStore())
    run = creator.create(BOOK)
    assert "audiobook_outline" not in run.plan.stages


def test_an_unknown_mode_is_refused_and_nothing_is_saved() -> None:
    runs = InMemoryRunRepository()
    with pytest.raises(ApplicationError) as refused:
        CreateRun(runs, InMemoryQueue()).create(BOOK, mode="podcast")
    assert refused.value.code == "RUN_MODE_UNKNOWN"
    assert list(runs.run_ids()) == []


def test_an_audiobook_of_a_screenplay_is_refused() -> None:
    runs = InMemoryRunRepository()
    with pytest.raises(ApplicationError) as refused:
        CreateRun(runs, InMemoryQueue(), artifacts=InMemoryArtifactStore()).create(
            BookBrief(BookKind.SCREENPLAY, "a film", 1_000_000), (SOURCE,), None, None, "audiobook"
        )
    assert refused.value.code == "RUN_KIND_UNSUPPORTED"
    assert list(runs.run_ids()) == []
