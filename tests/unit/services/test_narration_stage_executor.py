# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""NarrationStageExecutor: optional, default off, every chapter gated, the AI disclosure in the manifest."""

import asyncio
import io
import json
import math
import wave
from array import array

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.narrator_interface import NarratorInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.narration import Narration
from engineering_influence.services.narration_gate import NarrationGate
from engineering_influence.services.narration_stage_executor import NarrationStageExecutor
from engineering_influence.services.narration_text import NarrationText
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.outline_parser import OutlineParser

RATE = 2_000
OUTLINE = (
    "## Chapter 1: The Hive\nPurpose: How a colony works.\nBeats:\n- The queen\n\n"
    "## Chapter 2: The Site\nPurpose: Where to put it.\nBeats:\n- Sun\n"
)
CHAPTER_ONE = "# Chapter 1: The Hive\n\nBees live in colonies of tens of thousands."
CHAPTER_TWO = "# Chapter 2: The Site\n\nPut the hive where the morning sun reaches it."


class Tone(NarratorInterface):
    """A steady tone that takes 0.4 seconds a word, so the pace is natural; optionally broken."""

    def __init__(self, broken: str = "") -> None:
        self.broken = broken
        self.calls = 0

    def narrate(self, text: str) -> Narration:
        self.calls += 1
        if self.broken and self.broken in text:
            raise ApplicationError(
                code="ENGINE_DOWN", message="the engine stopped", http_status=503
            )
        count = int(len(text.split()) * 0.4 * RATE)
        samples = [0.2 * math.sin(2 * math.pi * 220 * i / RATE) for i in range(count)]
        return Narration(RATE, array("f", samples))


def world(
    narrator: NarratorInterface | None,
) -> tuple[NarrationStageExecutor, InMemoryArtifactStore]:
    store = InMemoryArtifactStore()
    for name, text in {
        "outline.md": OUTLINE,
        "manuscript/src/chapter_01.md": CHAPTER_ONE,
        "manuscript/src/chapter_02.md": CHAPTER_TWO,
    }.items():
        store.put("run-1", name, text.encode("utf-8"))
    return NarrationStageExecutor(
        store, OutlineParser(), narrator, NarrationText(), NarrationGate()
    ), store


def run(executor: NarrationStageExecutor, attempt: int = 1):  # type: ignore[no-untyped-def]
    brief = BookBrief(BookKind.NONFICTION, "bees", 5_000_000)
    book_run = BookRun(
        "run-1", brief, NonfictionRecipes().plan(), Budget(cap=5_000_000), stage="narration"
    )
    return asyncio.run(executor.execute(book_run, attempt))


def manifest(store: InMemoryArtifactStore) -> dict[str, object]:
    data = store.get("run-1", "narration.json")
    assert data is not None
    return json.loads(data.decode("utf-8"))


def test_with_no_narrator_the_book_is_recorded_as_not_narrated_and_nothing_else_is_made() -> None:
    executor, store = world(None)
    report = run(executor)
    assert report.issues == () and manifest(store) == {"status": "not_narrated"}
    assert store.get("run-1", "narration/chapter_01.wav") is None


def test_each_chapter_is_narrated_to_a_wav_and_the_manifest_carries_the_ai_disclosure() -> None:
    executor, store = world(Tone())
    report = run(executor)
    assert report.issues == ()
    data = store.get("run-1", "narration/chapter_01.wav")
    assert data is not None
    with wave.open(io.BytesIO(data), "rb") as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, RATE)
        assert wav.getnframes() > 0
    body = manifest(store)
    assert body["status"] == "narrated" and body["ai_narration"] is True
    assert "text-to-speech model" in str(body["disclosure"])
    assert [c["status"] for c in body["chapters"]] == ["narrated", "narrated"]  # type: ignore[index, union-attr]


def test_a_chapter_the_gate_refuses_is_not_kept_and_is_reported_without_stopping_the_run() -> None:
    class Silent(NarratorInterface):
        def narrate(self, text: str) -> Narration:
            return Narration(RATE, array("f", [0.0] * (RATE * 10)))

    executor, store = world(Silent())
    report = run(executor)
    assert store.get("run-1", "narration/chapter_01.wav") is None
    assert [issue.code for issue in report.issues] == ["NARRATION_REJECTED", "NARRATION_REJECTED"]
    assert "seconds of silence" in report.issues[0].detail
    assert not report.issues[0].blocking


def test_an_engine_that_fails_for_a_chapter_is_reported_and_the_others_are_still_narrated() -> None:
    executor, store = world(Tone(broken="colonies"))
    report = run(executor)
    assert [issue.code for issue in report.issues] == ["NARRATION_FAILED"]
    assert store.get("run-1", "narration/chapter_01.wav") is None
    assert store.get("run-1", "narration/chapter_02.wav") is not None


def test_a_redelivered_stage_narrates_only_the_chapters_that_are_not_done() -> None:
    narrator = Tone()
    executor, _store = world(narrator)
    run(executor)
    calls = narrator.calls
    run(executor, attempt=2)
    assert narrator.calls == calls


def test_a_chapter_missing_from_the_manuscript_is_a_missing_input() -> None:
    store = InMemoryArtifactStore()
    store.put("run-1", "outline.md", OUTLINE.encode("utf-8"))
    executor = NarrationStageExecutor(
        store, OutlineParser(), Tone(), NarrationText(), NarrationGate()
    )
    try:
        run(executor)
    except ApplicationError as error:
        assert error.code == "STAGE_INPUT_MISSING"
    else:
        raise AssertionError("a missing chapter must be refused")


def test_a_wav_that_already_exists_is_not_written_again_and_the_chapter_is_recorded() -> None:
    narrator = Tone()
    executor, store = world(narrator)
    store.put("run-1", "narration/chapter_01.wav", b"already there")
    run(executor)
    assert store.get("run-1", "narration/chapter_01.wav") == b"already there"
    assert manifest(store)["chapters"][0]["status"] == "narrated"  # type: ignore[index]


def test_a_narrator_that_changes_its_sample_rate_partway_is_a_failed_chapter() -> None:
    class Wobbling(NarratorInterface):
        def __init__(self) -> None:
            self.rate = RATE

        def narrate(self, text: str) -> Narration:
            self.rate = RATE * 2 if self.rate == RATE else RATE
            return Narration(self.rate, array("f", [0.1] * 10))

    executor, _store = world(Wobbling())
    report = run(executor)
    assert "NARRATION_FAILED" in [issue.code for issue in report.issues]
    assert "partway through a chapter" in report.issues[0].detail


def test_a_chapter_with_no_speakable_text_is_a_failed_chapter_not_a_crash() -> None:
    store = InMemoryArtifactStore()
    store.put("run-1", "outline.md", OUTLINE.encode("utf-8"))
    store.put("run-1", "manuscript/src/chapter_01.md", CHAPTER_ONE.encode("utf-8"))
    store.put("run-1", "manuscript/src/chapter_02.md", b"[^1]\n\n***")
    executor = NarrationStageExecutor(
        store, OutlineParser(), Tone(), NarrationText(), NarrationGate()
    )
    report = run(executor)
    assert [issue.code for issue in report.issues] == ["NARRATION_FAILED"]
    assert "no text to narrate" in report.issues[0].detail
