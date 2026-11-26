# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScreenplayReviseStageExecutor: a usable revision is kept, anything else keeps the draft, and money runs out gently."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.scene_reviser_interface import SceneReviserInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.scene_card import SceneCard
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.scene_card_list import SceneCardList
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes
from engineering_influence.services.screenplay_revise_stage_executor import (
    ScreenplayReviseStageExecutor,
)
from engineering_influence.services.screenplay_section_check import ScreenplaySectionCheck

CARDS = "\n".join(
    f"## S{n:02d} · scene {n}\n**What changes:** it changes.\n**Therefore:** next.\n**Beat:** Set-Up\n**Storyline:** A\n**Sources:** 001\n"
    for n in (1, 2, 3)
)
DRAFT = "INT. ROOM - DAY\n\nScene {} plays out."


class Reviser(SceneReviserInterface):
    """Answers with the given text for each scene, or raises the given error, and keeps the cards it was asked about."""

    def __init__(self, answer, raise_on: frozenset[int] = frozenset()) -> None:
        self.answer = answer
        self.raise_on = raise_on
        self.calls: list[int] = []

    def revise(self, run: BookRun, card: SceneCard, scene: str) -> str:
        self.calls.append(card.number)
        if card.number in self.raise_on:
            raise SpendConsentNeededError(1)
        return self.answer(card.number)


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000)
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def seeded(*drafts: int) -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.put("run-1", "scene_cards.md", CARDS.encode("utf-8"))
    for number in drafts:
        store.put("run-1", f"scenes/{number:03d}.md", DRAFT.format(number).encode("utf-8"))
    return store


def stage(store: InMemoryArtifactStore, reviser: Reviser) -> ScreenplayReviseStageExecutor:
    return ScreenplayReviseStageExecutor(
        store, reviser, SceneCardList(), ScreenplaySectionCheck(FountainParser())
    )


def revised(store: InMemoryArtifactStore, number: int) -> str:
    data = store.get("run-1", f"revised/{number:03d}.md")
    assert data is not None
    return data.decode("utf-8")


def test_a_usable_revision_of_the_same_length_is_kept() -> None:
    store = seeded(1, 2, 3)
    reviser = Reviser(lambda n: f"INT. ROOM - DAY\n\nScene {n} plays on.")
    asyncio.run(stage(store, reviser).execute(run(), 1))
    assert revised(store, 1) == "INT. ROOM - DAY\n\nScene 1 plays on."
    assert reviser.calls == [1, 2, 3]


def test_a_revision_that_breaks_the_format_keeps_the_draft() -> None:
    store = seeded(1, 2, 3)
    reviser = Reviser(lambda n: f"INT. ROOM - MORNING\n\nScene {n} plays on.")
    asyncio.run(stage(store, reviser).execute(run(), 1))
    assert revised(store, 2) == DRAFT.format(2)


def test_a_revision_outside_the_length_bounds_keeps_the_draft() -> None:
    store = seeded(1, 2, 3)
    reviser = Reviser(
        lambda n: f"INT. ROOM - DAY\n\nScene {n} plays on and on and on and on and on."
    )
    asyncio.run(stage(store, reviser).execute(run(), 1))
    assert revised(store, 3) == DRAFT.format(3)


def test_a_scene_already_revised_is_not_asked_again() -> None:
    store = seeded(1, 2, 3)
    store.put("run-1", "revised/001.md", b"already revised")
    reviser = Reviser(lambda n: f"INT. ROOM - DAY\n\nScene {n} plays on.")
    asyncio.run(stage(store, reviser).execute(run(), 2))
    assert reviser.calls == [2, 3]
    assert revised(store, 1) == "already revised"


def test_when_money_runs_out_that_scene_and_the_rest_keep_their_drafts() -> None:
    store = seeded(1, 2, 3)
    reviser = Reviser(lambda n: f"INT. ROOM - DAY\n\nScene {n} plays on.", raise_on=frozenset({2}))
    asyncio.run(stage(store, reviser).execute(run(), 1))
    assert reviser.calls == [1, 2]
    assert revised(store, 1) == "INT. ROOM - DAY\n\nScene 1 plays on."
    assert revised(store, 2) == DRAFT.format(2)
    assert revised(store, 3) == DRAFT.format(3)


def test_the_report_counts_the_scenes_that_kept_their_draft() -> None:
    store = seeded(1, 2, 3)
    reviser = Reviser(
        lambda n: (
            "INT. ROOM - MORNING\n\nBad." if n == 2 else f"INT. ROOM - DAY\n\nScene {n} plays on."
        )
    )
    report = asyncio.run(stage(store, reviser).execute(run(), 1))
    assert len(report.issues) == 1
    assert report.issues[0].code == "revision-kept-draft"
    assert report.issues[0].blocking is False
    assert "1 of 3 scenes" in report.issues[0].detail


def test_a_report_with_every_revision_kept_has_no_issue() -> None:
    store = seeded(1, 2, 3)
    reviser = Reviser(lambda n: f"INT. ROOM - DAY\n\nScene {n} plays on.")
    report = asyncio.run(stage(store, reviser).execute(run(), 1))
    assert report.issues == ()


def test_an_unusable_answer_stops_the_stage() -> None:
    class Stops(Reviser):
        def revise(self, run: BookRun, card: SceneCard, scene: str) -> str:
            raise ApplicationError(code="STAGE_ANSWER_UNUSABLE", message="cut off", http_status=502)

    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(seeded(1, 2, 3), Stops(lambda n: "")).execute(run(), 1))
    assert error.value.code == "STAGE_ANSWER_UNUSABLE"


def test_a_scene_that_was_never_drafted_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(seeded(1, 2), Reviser(lambda n: "")).execute(run(), 1))
    assert error.value.code == "STAGE_INPUT_MISSING"
