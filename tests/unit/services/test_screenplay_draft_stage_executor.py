# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayDraftStageExecutor: scenes drafted in order and checked, one retry, resume, and the assembled script."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.scene_drafter_interface import SceneDrafterInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.scene_card import SceneCard
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.scene_card_list import SceneCardList
from engineering_influence.services.screenplay_assembler import ScreenplayAssembler
from engineering_influence.services.screenplay_draft_stage_executor import (
    ScreenplayDraftStageExecutor,
)
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes
from engineering_influence.services.screenplay_scene_cards_check import ScreenplaySceneCardsCheck
from engineering_influence.services.screenplay_section_check import ScreenplaySectionCheck

BEATS = ["Opening Image", "Set-Up", "All Is Lost", "Closing Image"]
CARDS = "\n".join(
    f"## S{n:02d} · scene {n}\n**What changes:** it changes.\n**Therefore:** next.\n**Beat:** {beat}\n**Storyline:** A\n**Sources:** 001\n"
    for n, beat in enumerate(BEATS, 1)
)


class Drafter(SceneDrafterInterface):
    """Writes a good scene for each card, except the cards named in `bad`, which fail a format rule the first time."""

    def __init__(self, bad: frozenset[int] = frozenset()) -> None:
        self.bad = bad
        self.calls: list[int] = []
        self.sources: dict[int, str] = {}
        self._failed: set[int] = set()

    def draft(
        self, run: BookRun, card: SceneCard, anchors: str, beats: str, sources: str, try_number: int
    ) -> str:
        self.calls.append(card.number)
        self.sources[card.number] = sources
        if card.number in self.bad and card.number not in self._failed:
            self._failed.add(card.number)
            return f"INT. ROOM - MORNING\n\nScene {card.number}."
        return f"INT. ROOM - DAY\n\nScene {card.number} plays out."


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000, title_hint="TEST FILM")
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def stage(
    store: InMemoryArtifactStore, drafter: Drafter, shareable: frozenset[int] = frozenset()
) -> ScreenplayDraftStageExecutor:
    return ScreenplayDraftStageExecutor(
        store,
        drafter,
        SceneCardList(),
        ScreenplaySectionCheck(FountainParser()),
        ScreenplayAssembler(FountainParser()),
        shareable,
    )


def seeded() -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.put("run-1", "scene_cards.md", CARDS.encode("utf-8"))
    store.put("run-1", "anchors.md", b"anchors")
    store.put("run-1", "beats.md", b"beats")
    store.put("run-1", "source/001.md", b"the first source")
    return store


def text(store: InMemoryArtifactStore, name: str) -> str:
    data = store.get("run-1", name)
    assert data is not None
    return data.decode("utf-8")


def test_each_scene_is_drafted_in_order_and_the_script_is_assembled() -> None:
    store, drafter = seeded(), Drafter()
    asyncio.run(stage(store, drafter).execute(run(), 1))
    assert drafter.calls == [1, 4, 3, 2]
    script = text(store, "screenplay.fountain")
    assert script.startswith("Title: TEST FILM\n\nFADE IN:")
    assert (
        script.index("Scene 1 plays")
        < script.index("Scene 2 plays")
        < script.index("Scene 4 plays")
    )
    assert script.endswith("FADE OUT.\n\n>THE END<\n")


def test_a_scene_that_fails_its_check_is_drafted_once_more() -> None:
    store, drafter = seeded(), Drafter(bad=frozenset({2}))
    asyncio.run(stage(store, drafter).execute(run(), 1))
    assert drafter.calls.count(2) == 2
    assert "Scene 2 plays out." in text(store, "scenes/002.md")


def test_a_scene_that_fails_twice_stops_the_stage_with_its_problems() -> None:
    class Always(Drafter):
        def draft(
            self,
            run: BookRun,
            card: SceneCard,
            anchors: str,
            beats: str,
            sources: str,
            try_number: int,
        ) -> str:
            return "INT. ROOM - MORNING\n\nNever right."

    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(seeded(), Always()).execute(run(), 1))
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert error.value.message.startswith("S01: ")
    assert "time 'MORNING' is not one of" in error.value.message


def test_a_redelivered_stage_drafts_only_what_is_missing() -> None:
    store, drafter = seeded(), Drafter()
    asyncio.run(stage(store, drafter).execute(run(), 1))
    again = Drafter()
    asyncio.run(stage(store, again).execute(run(), 2))
    assert again.calls == []


def test_the_shareable_scenes_are_drafted_last() -> None:
    store, drafter = seeded(), Drafter()
    asyncio.run(stage(store, drafter, shareable=frozenset({2})).execute(run(), 1))
    assert drafter.calls == [1, 4, 3, 2]


def test_missing_input_is_refused() -> None:
    store = InMemoryArtifactStore()
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(store, Drafter()).execute(run(), 1))
    assert error.value.code in {"STAGE_INPUT_MISSING", "SCENE_CARDS_UNREADABLE"}


def test_a_card_without_a_beat_is_unreadable() -> None:
    with pytest.raises(ApplicationError) as error:
        SceneCardList().parse("## S01 · no beat\n**What changes:** x\n")
    assert error.value.code == "SCENE_CARDS_UNREADABLE"


def test_the_scene_cards_are_read_with_their_beats() -> None:
    cards = SceneCardList().parse(CARDS)
    assert [(c.number, c.beat) for c in cards] == list(enumerate(BEATS, 1))
    assert cards[0].artifact() == "scenes/001.md"


def test_a_scene_card_number_starts_at_one() -> None:
    with pytest.raises(ValueError, match="numbered from 1"):
        SceneCard(0, "Set-Up", "x", (1,))


def test_the_card_check_is_the_same_as_the_stage_reads() -> None:
    assert ScreenplaySceneCardsCheck().problems(CARDS) == ()


def test_a_scene_card_names_its_beat() -> None:
    with pytest.raises(ValueError, match="names its beat"):
        SceneCard(1, "  ", "body", (1,))


def test_text_with_no_card_is_unreadable() -> None:
    with pytest.raises(ApplicationError) as error:
        SceneCardList().parse("# Cards\n\nNothing here.\n")
    assert error.value.code == "SCENE_CARDS_UNREADABLE"


def test_the_plan_drafts_scenes_after_the_architecture() -> None:
    assert tuple(ScreenplayRecipes().plan().stages) == (
        "brief",
        "anchors",
        "audit",
        "beats",
        "scene_cards",
        "visual_grammar",
        "draft",
    )


def test_the_title_is_the_brief_title_or_untitled() -> None:
    titled = ScreenplayDraftStageExecutor._title_page(run())
    assert titled == (("Title", "TEST FILM"),)
    untitled_brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000)
    untitled = BookRun(
        run_id="run-2",
        brief=untitled_brief,
        plan=ScreenplayRecipes().plan(),
        budget=Budget(cap=5_000_000),
    )
    assert ScreenplayDraftStageExecutor._title_page(untitled) == (("Title", "UNTITLED"),)


def with_cards(cards: str, *sources: tuple[str, bytes]) -> InMemoryArtifactStore:
    """A run holding the given cards, the anchors and beats, and the given source files."""
    store = InMemoryArtifactStore()
    store.put("run-1", "scene_cards.md", cards.encode("utf-8"))
    store.put("run-1", "anchors.md", b"anchors")
    store.put("run-1", "beats.md", b"beats")
    for name, data in sources:
        store.put("run-1", name, data)
    return store


def test_each_scene_is_drafted_from_only_the_sources_its_card_cites() -> None:
    cards = CARDS.replace("**Sources:** 001", "**Sources:** 002", 1)
    store = with_cards(
        cards, ("source/001.md", b"the first source"), ("source/002.md", b"the second source")
    )
    drafter = Drafter()
    asyncio.run(stage(store, drafter).execute(run(), 1))
    assert drafter.sources[1] == "Source 002:\nthe second source"
    assert drafter.sources[2] == "Source 001:\nthe first source"


def test_a_card_citing_a_source_the_run_does_not_hold_stops_the_stage() -> None:
    cards = CARDS.replace("**Sources:** 001", "**Sources:** 009", 1)
    store = with_cards(cards, ("source/001.md", b"the first source"))
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(store, Drafter()).execute(run(), 1))
    assert error.value.code == "STAGE_INPUT_MISSING"
