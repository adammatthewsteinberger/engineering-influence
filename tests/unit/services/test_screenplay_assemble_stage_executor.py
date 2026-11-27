# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayAssembleStageExecutor: the revised scenes in card order make one script, refused if it miscounts or breaks the format."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.scene_card_list import SceneCardList
from engineering_influence.services.screenplay_assemble_stage_executor import (
    ScreenplayAssembleStageExecutor,
)
from engineering_influence.services.screenplay_assembler import ScreenplayAssembler
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes

CARDS = "\n".join(
    f"## S{n:02d} · scene {n}\n**What changes:** it changes.\n**Therefore:** next.\n**Beat:** Set-Up\n**Storyline:** A\n**Sources:** 001\n"
    for n in (1, 2)
)
GOOD_ONE = "INT. ROOM - DAY\n\nScene one plays out."
GOOD_TWO = "EXT. STREET - NIGHT\n\nScene two plays out."


def run(title: str | None = "TEST FILM") -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000, title_hint=title)
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def stage(store: InMemoryArtifactStore) -> ScreenplayAssembleStageExecutor:
    return ScreenplayAssembleStageExecutor(
        store, SceneCardList(), ScreenplayAssembler(FountainParser()), FountainParser()
    )


def with_revised(*scenes: str, cards: str = CARDS) -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.put("run-1", "scene_cards.md", cards.encode("utf-8"))
    for number, scene in enumerate(scenes, 1):
        store.put("run-1", f"dialogued/{number:03d}.md", scene.encode("utf-8"))
    return store


def assemble(store: InMemoryArtifactStore, title: str | None = "TEST FILM") -> None:
    asyncio.run(stage(store).execute(run(title), 1))


def script(store: InMemoryArtifactStore) -> str:
    data = store.get("run-1", "screenplay.fountain")
    assert data is not None
    return data.decode("utf-8")


def test_the_revised_scenes_are_assembled_in_card_order_under_the_title() -> None:
    store = with_revised(GOOD_ONE, GOOD_TWO)
    assemble(store)
    text = script(store)
    assert text.startswith("Title: TEST FILM\n\nFADE IN:")
    assert text.index("Scene one plays") < text.index("Scene two plays")
    assert text.endswith("FADE OUT.\n\n>THE END<\n")


def test_an_untitled_brief_gets_the_untitled_title_page() -> None:
    store = with_revised(GOOD_ONE, GOOD_TWO)
    assemble(store, title=None)
    assert script(store).startswith("Title: UNTITLED")


def test_a_revised_scene_with_two_headings_is_refused_by_the_assembler() -> None:
    store = with_revised(f"{GOOD_ONE}\n\n{GOOD_TWO}", GOOD_TWO)
    with pytest.raises(ApplicationError) as error:
        assemble(store)
    assert error.value.code == "SCREENPLAY_SCENE_INVALID"
    assert store.get("run-1", "screenplay.fountain") is None


def test_a_script_that_breaks_the_format_rules_is_refused() -> None:
    store = with_revised(GOOD_ONE, "INT. ROOM - MORNING\n\nScene two plays out.")
    with pytest.raises(ApplicationError) as error:
        assemble(store)
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert "breaks the format rules" in error.value.message


def test_a_scene_that_was_never_revised_is_refused() -> None:
    store = with_revised(GOOD_ONE)
    with pytest.raises(ApplicationError) as error:
        assemble(store)
    assert error.value.code == "STAGE_INPUT_MISSING"
