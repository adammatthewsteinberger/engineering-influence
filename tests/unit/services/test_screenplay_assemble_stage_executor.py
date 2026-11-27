# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayAssembleStageExecutor: the revised scenes in card order make one script, refused if it miscounts, breaks the
format, or puts a beat out of place."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.services.fountain_page_estimate import FountainPageEstimate
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.interfaces.screenplay_beat_position_check_interface import (
    ScreenplayBeatPositionCheckInterface,
)
from engineering_influence.services.scene_card_list import SceneCardList
from engineering_influence.services.screenplay_assemble_stage_executor import (
    ScreenplayAssembleStageExecutor,
)
from engineering_influence.services.screenplay_assembler import ScreenplayAssembler
from engineering_influence.services.screenplay_beat_position_check import (
    ScreenplayBeatPositionCheck,
)
from engineering_influence.services.screenplay_beat_sheet_check import ScreenplayBeatSheetCheck
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes

CARDS = "\n".join(
    f"## S{n:02d} · scene {n}\n**What changes:** it changes.\n**Therefore:** next.\n**Beat:** Set-Up\n**Storyline:** A\n**Sources:** 001\n"
    for n in (1, 2)
)
GOOD_ONE = "INT. ROOM - DAY\n\nScene one plays out."
GOOD_TWO = "EXT. STREET - NIGHT\n\nScene two plays out."


class Placed(ScreenplayBeatPositionCheckInterface):
    """Every beat is taken to be placed. These tests are about the stage; the position check has its own tests, so the
    stage tests above need no beat sheet."""

    def problems(self, beat_sheet: str, scenes: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
        return ()


def run(title: str | None = "TEST FILM") -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000, title_hint=title)
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def stage(store: InMemoryArtifactStore) -> ScreenplayAssembleStageExecutor:
    return ScreenplayAssembleStageExecutor(
        store, SceneCardList(), ScreenplayAssembler(FountainParser()), FountainParser(), Placed()
    )


def with_revised(*scenes: str, cards: str = CARDS) -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.put("run-1", "scene_cards.md", cards.encode("utf-8"))
    store.put("run-1", "beats.md", b"")  # the fake placement ignores the beat sheet
    for number, scene in enumerate(scenes, 1):
        store.put("run-1", f"dialogued/{number:03d}.md", scene.encode("utf-8"))
    return store


def assemble(store: InMemoryArtifactStore, title: str | None = "TEST FILM") -> None:
    asyncio.run(stage(store).execute(run(title), 1))


def script(store: InMemoryArtifactStore) -> str:
    data = store.get("run-1", "screenplay.fountain")
    assert data is not None
    return data.decode("utf-8")


def fifteen_cards(beats: tuple[str, ...] = ScreenplayBeatSheetCheck.BEATS) -> str:
    """One card per beat, in the order given, each with its own scene number."""
    return "\n".join(
        f"## S{n:02d} · scene {n}\n**What changes:** it changes.\n**Therefore:** next.\n"
        f"**Beat:** {beat}\n**Storyline:** A\n**Sources:** 001\n"
        for n, beat in enumerate(beats, 1)
    )


def numbered(count: int) -> tuple[str, ...]:
    """Scenes of one size each, so that every scene takes the same number of lines."""
    return tuple(f"INT. ROOM {n} - DAY\n\nScene {n} plays out." for n in range(1, count + 1))


def beat_sheet(starts: dict[str, int] | None = None) -> str:
    """A beat sheet for a fifteen-page film: each beat planned at its own card's page unless a start is given."""
    rows = [
        "| Beat | Pages | Scenes | Scene | Central character | Function |",
        "|---|---|---|---|---|---|",
    ]
    for index, beat in enumerate(ScreenplayBeatSheetCheck.BEATS, 1):
        page = (starts or {}).get(beat, index)
        rows.append(f"| {beat} | {page} to {page} | 1 | scene | character | none |")
    return "\n".join(rows) + "\n"


def placed_store(cards: str, sheet: str, count: int) -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.put("run-1", "scene_cards.md", cards.encode("utf-8"))
    store.put("run-1", "beats.md", sheet.encode("utf-8"))
    for number, scene in enumerate(numbered(count), 1):
        store.put("run-1", f"dialogued/{number:03d}.md", scene.encode("utf-8"))
    return store


def assemble_with_beats(store: InMemoryArtifactStore) -> None:
    """The stage with the real position check, for a fifteen-page film."""
    parser = FountainParser()
    stage_with_beats = ScreenplayAssembleStageExecutor(
        store,
        SceneCardList(),
        ScreenplayAssembler(parser),
        parser,
        ScreenplayBeatPositionCheck(FountainPageEstimate(parser), 15),
    )
    asyncio.run(stage_with_beats.execute(run(), 1))


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


def test_a_beat_that_begins_out_of_place_stops_the_stage_with_the_beat_named() -> None:
    # All Is Lost is the eleventh of fifteen cards (67%), but the sheet plans it on page 14 (87%).
    store = placed_store(fifteen_cards(), beat_sheet({"All Is Lost": 14}), 15)
    with pytest.raises(ApplicationError) as error:
        assemble_with_beats(store)
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert error.value.message.startswith("the beats do not fall where the beat sheet puts them: ")
    assert (
        "All Is Lost begins 67% of the way through the script; the beat sheet puts it at 87%"
        in error.value.message
    )
    assert store.get("run-1", "screenplay.fountain") is None


def test_a_beat_with_no_scene_card_stops_the_stage() -> None:
    beats = tuple(beat for beat in ScreenplayBeatSheetCheck.BEATS if beat != "Finale")
    store = placed_store(fifteen_cards(beats), beat_sheet(), 14)
    with pytest.raises(ApplicationError) as error:
        assemble_with_beats(store)
    assert "Finale: no scene card is tagged with it" in error.value.message


def test_beats_placed_where_the_sheet_puts_them_are_stored() -> None:
    store = placed_store(fifteen_cards(), beat_sheet(), 15)
    assemble_with_beats(store)
    assert script(store).startswith("Title: TEST FILM\n\nFADE IN:")
