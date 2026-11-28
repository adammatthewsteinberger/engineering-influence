# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ScenePassStageExecutor: a usable answer is kept, an unusable one carries the scene forward, and a run out of money carries
the rest forward; a scene already passed is not passed again."""

import asyncio

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
from engineering_influence.services.scene_pass_stage_executor import ScenePassStageExecutor
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes
from engineering_influence.services.screenplay_section_check import ScreenplaySectionCheck

CARDS = "\n".join(
    f"## S{n:02d} · scene {n}\n**What changes:** it changes.\n**Therefore:** next.\n**Beat:** Set-Up\n"
    f"**Storyline:** A\n**Sources:** 001\n"
    for n in (1, 2)
)


class Passer(SceneReviserInterface):
    """Answers each scene with `answers[number]`; raises when `broke` says the money has run out."""

    def __init__(self, answers: dict[int, str], broke: bool = False) -> None:
        self.answers = answers
        self.broke = broke
        self.calls: list[int] = []

    def revise(self, run: BookRun, card: SceneCard, scene: str) -> str:
        self.calls.append(card.number)
        if self.broke:
            raise SpendConsentNeededError(1)
        return self.answers[card.number]


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000)
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def store(*scenes: str) -> InMemoryArtifactStore:
    s = InMemoryArtifactStore()
    s.put("run-1", "scene_cards.md", CARDS.encode("utf-8"))
    for number, scene in enumerate(scenes, 1):
        s.put("run-1", f"revised/{number:03d}.md", scene.encode("utf-8"))
    return s


def stage(s: InMemoryArtifactStore, passer: Passer) -> ScenePassStageExecutor:
    return ScenePassStageExecutor(
        s,
        "structure_scenes",
        passer,
        SceneCardList(),
        ScreenplaySectionCheck(FountainParser()),
        lambda card: card.revised(),
        lambda card: card.structured(),
    )


def text(s: InMemoryArtifactStore, name: str) -> str:
    data = s.get("run-1", name)
    assert data is not None
    return data.decode("utf-8")


ONE = "INT. ROOM - DAY\n\nScene one plays out in full, with nothing added to it."
TWO = "INT. YARD - NIGHT\n\nScene two plays out in full, with nothing added to it."


def test_a_usable_answer_is_kept() -> None:
    s = store(ONE, TWO)
    asyncio.run(
        stage(s, Passer({1: ONE.replace("nothing added", "nothing added here"), 2: TWO})).execute(
            run(), 1
        )
    )
    assert "nothing added here" in text(s, "structured/001.md")


def test_an_unusable_answer_carries_the_scene_forward_unchanged() -> None:
    s = store(ONE, TWO)
    asyncio.run(stage(s, Passer({1: "not a scene", 2: TWO})).execute(run(), 1))
    assert text(s, "structured/001.md") == ONE


def test_running_out_of_money_carries_the_rest_forward_unchanged() -> None:
    s = store(ONE, TWO)
    passer = Passer({}, broke=True)
    asyncio.run(stage(s, passer).execute(run(), 1))
    assert text(s, "structured/001.md") == ONE
    assert text(s, "structured/002.md") == TWO
    assert passer.calls == [1]


def test_a_scene_already_passed_is_not_passed_again() -> None:
    s = store(ONE, TWO)
    s.put("run-1", "structured/001.md", ONE.encode("utf-8"))
    passer = Passer({2: TWO})
    asyncio.run(stage(s, passer).execute(run(), 1))
    assert passer.calls == [2]


def test_a_scene_with_no_input_stops_the_stage() -> None:
    import pytest

    from engineering_influence.errors.application_error import ApplicationError

    s = store(ONE)
    with pytest.raises(ApplicationError) as refused:
        asyncio.run(stage(s, Passer({1: ONE})).execute(run(), 1))
    assert refused.value.code == "STAGE_INPUT_MISSING"
