# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""VideoStageExecutor: shots stored once each, priced before the first paid call, refused past the budget, and never
generated without a provider."""

import asyncio
import json

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.video_generator_interface import VideoGeneratorInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.video_shot import VideoShot
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes
from engineering_influence.services.video_stage_executor import VideoStageExecutor

SHOTS = (
    VideoShot(1, 1, "minimax/hailuo-3", 4, "one"),
    VideoShot(2, 1, "minimax/hailuo-3", 4, "one"),
    VideoShot(3, 2, "alibaba/wan-3.0", 20, "two"),
)


class Builder:
    """Returns the shots, and records the script it was given."""

    def __init__(self) -> None:
        self.scripts: list[str] = []

    def build(self, script: str) -> tuple[VideoShot, ...]:
        self.scripts.append(script)
        return SHOTS


class Generator(VideoGeneratorInterface):
    def __init__(self) -> None:
        self.made: list[int] = []

    def generate(self, shot: VideoShot) -> bytes:
        self.made.append(shot.number)
        return f"mp4-{shot.number}".encode()


class PerSecond:
    """A stand-in price: one micro-dollar a second, so the costs are easy to read."""

    def cost_micro_usd(self, shots: tuple[VideoShot, ...]) -> int:
        return sum(shot.seconds() for shot in shots)


def run(cap: int = 1_000) -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000, title_hint="TEST FILM")
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=cap)
    )


def stage(
    store: InMemoryArtifactStore, generator: Generator | None, builder: Builder | None = None
) -> VideoStageExecutor:
    return VideoStageExecutor(store, builder or Builder(), PerSecond(), generator)


def seeded(name: str = "screenplay.fountain") -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.put("run-1", name, b"INT. ROOM - DAY\n\nText.\n")
    return store


def manifest(store: InMemoryArtifactStore) -> dict:
    data = store.get("run-1", "video/manifest.json")
    assert data is not None
    return json.loads(data)


def test_with_no_provider_the_stage_records_that_no_video_was_made() -> None:
    store = seeded()
    asyncio.run(stage(store, None).execute(run(), 1))
    assert manifest(store)["status"] == "not_generated"
    assert manifest(store)["ai_generated"] is False
    assert store.get("run-1", "video/shot_001.mp4") is None


def test_a_missing_manifest_is_written_once_with_no_provider() -> None:
    store = seeded()
    asyncio.run(stage(store, None).execute(run(), 1))
    first = store.get("run-1", "video/manifest.json")
    asyncio.run(stage(store, None).execute(run(), 2))
    assert store.get("run-1", "video/manifest.json") == first


def test_each_shot_is_generated_and_stored_with_an_ai_manifest() -> None:
    store, generator = seeded(), Generator()
    asyncio.run(stage(store, generator).execute(run(), 1))
    assert generator.made == [1, 2, 3]
    assert store.get("run-1", "video/shot_003.mp4") == b"mp4-3"
    data = manifest(store)
    assert data["status"] == "generated" and data["ai_generated"] is True
    assert data["estimated_micro_usd"] == 4 + 4 + 20
    assert [entry["file"] for entry in data["shots"]] == [
        "video/shot_001.mp4",
        "video/shot_002.mp4",
        "video/shot_003.mp4",
    ]


def test_a_shot_already_stored_is_not_generated_again() -> None:
    store = seeded()
    store.put("run-1", "video/shot_001.mp4", b"kept")
    generator = Generator()
    asyncio.run(stage(store, generator).execute(run(), 1))
    assert generator.made == [2, 3]
    assert store.get("run-1", "video/shot_001.mp4") == b"kept"


def test_the_shots_not_yet_stored_must_fit_the_budget() -> None:
    store, generator = seeded(), Generator()
    with pytest.raises(SpendConsentNeededError) as error:
        asyncio.run(stage(store, generator).execute(run(cap=20), 1))
    assert error.value.requested_micro_usd == (4 + 4 + 20) - 20
    assert generator.made == []


def test_the_shooting_script_is_planned_when_the_lock_stage_stored_one() -> None:
    store = seeded()
    store.put("run-1", "shooting_script.fountain", b"LOCKED\n")
    builder = Builder()
    asyncio.run(stage(store, None, builder).execute(run(), 1))
    assert builder.scripts == ["LOCKED\n"]


def test_a_run_with_no_script_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(InMemoryArtifactStore(), None).execute(run(), 1))
    assert error.value.code == "STAGE_INPUT_MISSING"
