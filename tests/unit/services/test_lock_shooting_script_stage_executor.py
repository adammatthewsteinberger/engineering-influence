# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""LockShootingScriptStageExecutor: the scenes are numbered once, the numbers are kept when the stage runs again, and a
script that does not match its cards, or a locked scene that has moved, is refused."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.lock_shooting_script_stage_executor import (
    LockShootingScriptStageExecutor,
)
from engineering_influence.services.scene_card_list import SceneCardList
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes
from engineering_influence.services.shooting_lock_codec import ShootingLockCodec
from engineering_influence.services.shooting_lock_planner import ShootingLockPlanner
from engineering_influence.services.shooting_script_renderer import ShootingScriptRenderer

SCRIPT = (
    "Title: TEST FILM\n\nFADE IN:\n\nINT. ROOM - DAY\n\nScene one.\n\n"
    "EXT. YARD - NIGHT\n\nScene two.\n\nINT. HALL - DAY\n\nScene three.\n\nFADE OUT.\n"
)


TWO_SCENES = "Title: TEST FILM\n\nFADE IN:\n\nINT. ROOM - DAY\n\nScene one.\n\nINT. HALL - DAY\n\nScene three.\n"


def card(number: int) -> str:
    return (
        f"## S{number:02d} · scene {number}\n**What changes:** it changes.\n**Therefore:** next.\n"
        f"**Beat:** Set-Up\n**Storyline:** A\n**Sources:** 001\n"
    )


def cards(*numbers: int) -> str:
    return "\n".join(card(number) for number in numbers)


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000, title_hint="TEST FILM")
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def stage(store: InMemoryArtifactStore) -> LockShootingScriptStageExecutor:
    return LockShootingScriptStageExecutor(
        store,
        SceneCardList(),
        FountainParser(),
        ShootingLockPlanner(),
        ShootingLockCodec(),
        ShootingScriptRenderer(FountainParser()),
    )


def seeded(card_text: str, script: str = SCRIPT) -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.put("run-1", "scene_cards.md", card_text.encode("utf-8"))
    store.put("run-1", "screenplay.fountain", script.encode("utf-8"))
    return store


def text(store: InMemoryArtifactStore, name: str) -> str:
    data = store.get("run-1", name)
    assert data is not None
    return data.decode("utf-8")


def refused(store: InMemoryArtifactStore, code: str) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(store).execute(run(), 1))
    assert error.value.code == code
    return error.value


def test_the_scenes_are_numbered_and_the_lock_is_stored() -> None:
    store = seeded(cards(1, 2, 3))
    asyncio.run(stage(store).execute(run(), 1))
    labels = [
        entry.label
        for entry in ShootingLockCodec().decode(text(store, "shooting_lock.json")).entries
    ]
    assert labels == ["1", "2", "3"]
    assert "INT. ROOM - DAY #1#" in text(store, "shooting_script.fountain")
    assert "INT. HALL - DAY #3#" in text(store, "shooting_script.fountain")


def locked_run(
    card_text: str, script: str, previous: InMemoryArtifactStore
) -> InMemoryArtifactStore:
    """A new run with the given cards and script, carrying the lock the previous run stored: the store refuses to
    overwrite an artifact, so a later run is a new store holding what it kept."""
    store = seeded(card_text, script)
    lock = previous.get("run-1", "shooting_lock.json")
    assert lock is not None
    store.put("run-1", "previous_shooting_lock.json", lock)
    return store


def test_a_carried_lock_keeps_every_number_it_gave() -> None:
    first = seeded(cards(1, 2, 3))
    asyncio.run(stage(first).execute(run(), 1))
    store = locked_run(cards(1, 3), TWO_SCENES, first)
    asyncio.run(stage(store).execute(run(), 2))
    shooting = text(store, "shooting_script.fountain")
    assert "INT. HALL - DAY #3#" in shooting
    assert ".OMITTED #2#" in shooting


def test_a_script_with_another_number_of_scenes_than_its_cards_is_refused() -> None:
    error = refused(seeded(cards(1, 2, 3, 4)), "STAGE_OUTPUT_INVALID")
    assert "the script has 3 scenes but the scene cards name 4" in error.message


def test_a_locked_scene_that_has_moved_is_refused() -> None:
    first = seeded(cards(1, 2, 3))
    asyncio.run(stage(first).execute(run(), 1))
    error = refused(locked_run(cards(2, 1, 3), SCRIPT, first), "STAGE_OUTPUT_INVALID")
    assert "has moved" in error.message


def test_a_lock_that_cannot_be_read_is_refused() -> None:
    store = seeded(cards(1, 2, 3))
    store.put("run-1", "previous_shooting_lock.json", b"not a lock")
    refused(store, "SHOOTING_LOCK_UNREADABLE")


def test_a_run_without_its_script_is_refused() -> None:
    store = InMemoryArtifactStore()
    store.put("run-1", "scene_cards.md", cards(1).encode("utf-8"))
    refused(store, "STAGE_INPUT_MISSING")
