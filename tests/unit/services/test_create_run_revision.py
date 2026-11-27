# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A previous shooting script given to a screenplay run is kept as its baseline, with the revision number; other kinds of run and out-of-range numbers are refused."""

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
from engineering_influence.services.shooting_revision_marks import ShootingRevisionMarks

SCREENPLAY = BookBrief(BookKind.SCREENPLAY, "a film", 1_000_000)
SOURCE = SourceEntry(1, "Ada sails.", "0" * 64)
BASELINE = "FADE IN:\n\nINT. ROOM - DAY #1#\n\nAda waits.\n"


def test_the_baseline_and_revision_are_kept_under_their_artifact_names() -> None:
    store = InMemoryArtifactStore()
    creator = CreateRun(InMemoryRunRepository(), InMemoryQueue(), artifacts=store)
    run = creator.create(SCREENPLAY, (SOURCE,), previous_script=BASELINE, revision=3)
    assert store.get(run.run_id, ShootingRevisionMarks.BASELINE) == BASELINE.encode("utf-8")
    assert store.get(run.run_id, ShootingRevisionMarks.REVISION) == b"3"


def test_a_baseline_is_refused_for_a_book_that_is_not_a_screenplay_and_no_run_is_saved() -> None:
    runs = InMemoryRunRepository()
    plan = StagePlan(BookKind.NONFICTION, ("brief", "build"))
    creator = CreateRun(
        runs, InMemoryQueue(), {BookKind.NONFICTION: plan}, artifacts=InMemoryArtifactStore()
    )
    with pytest.raises(ApplicationError) as refused:
        creator.create(BookBrief(BookKind.NONFICTION, "bees", 1_000_000), previous_script=BASELINE)
    assert refused.value.code == "RUN_KIND_UNSUPPORTED"
    assert list(runs.run_ids()) == []


@pytest.mark.parametrize("revision", [0, 10])
def test_a_revision_outside_the_colours_is_refused(revision: int) -> None:
    creator = CreateRun(InMemoryRunRepository(), InMemoryQueue(), artifacts=InMemoryArtifactStore())
    with pytest.raises(ApplicationError) as refused:
        creator.create(SCREENPLAY, (SOURCE,), revision=revision)
    assert refused.value.code == "RUN_REVISION_INVALID"


def test_a_baseline_is_refused_by_a_build_that_cannot_keep_it() -> None:
    creator = CreateRun(InMemoryRunRepository(), InMemoryQueue())
    with pytest.raises(ApplicationError) as refused:
        creator.create(SCREENPLAY, (SOURCE,), previous_script=BASELINE)
    assert refused.value.code == "SOURCES_NOT_STORED"
