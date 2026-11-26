# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A run given a stop stage has a plan that ends at that stage; a stage the plan does not have is refused before anything is saved."""

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
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes

FILM = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000)
SOURCE = SourceEntry(1, "one", hashlib.sha256(b"one").hexdigest())


def test_the_plan_ends_at_the_stop_stage() -> None:
    creator = CreateRun(InMemoryRunRepository(), InMemoryQueue(), artifacts=InMemoryArtifactStore())
    run = creator.create(FILM, (SOURCE,), None, "scene_cards")
    full = tuple(ScreenplayRecipes().plan().stages)
    assert tuple(run.plan.stages) == full[: full.index("scene_cards") + 1]


def test_a_run_without_a_stop_stage_keeps_its_whole_plan() -> None:
    creator = CreateRun(InMemoryRunRepository(), InMemoryQueue(), artifacts=InMemoryArtifactStore())
    run = creator.create(FILM, (SOURCE,))
    assert tuple(run.plan.stages) == tuple(ScreenplayRecipes().plan().stages)


def test_a_stage_the_plan_does_not_have_is_refused_and_nothing_is_saved() -> None:
    runs = InMemoryRunRepository()
    creator = CreateRun(runs, InMemoryQueue(), artifacts=InMemoryArtifactStore())
    with pytest.raises(ApplicationError) as refused:
        creator.create(FILM, (SOURCE,), None, "no_such_stage")
    assert refused.value.code == "STOP_STAGE_UNKNOWN"
    assert list(runs.run_ids()) == []
