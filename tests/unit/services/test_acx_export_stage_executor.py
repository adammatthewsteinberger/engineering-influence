# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""AcxExportStageExecutor: each part as speakable text and as audio, and a manifest that does not assume Virtual Voice."""

import asyncio
import io
import json
import math
import wave
from array import array

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.narrator_interface import NarratorInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.narration import Narration
from engineering_influence.services.acx_export_stage_executor import AcxExportStageExecutor
from engineering_influence.services.dash_rewriter import DashRewriter
from engineering_influence.services.metadata_parser import MetadataParser
from engineering_influence.services.narration_gate import NarrationGate
from engineering_influence.services.narration_text import NarrationText
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.outline_parser import OutlineParser

RATE = 16_000
OUTLINE = (
    "## Chapter 1: The Hive\nPurpose: How a colony works.\nBeats:\n- The queen\n\n"
    "## Chapter 2: The Site\nPurpose: Where to put it.\nBeats:\n- Sun\n"
)
LISTING = (
    "Title: Hive Mind\nSubtitle: A calm guide\nDescription:\n"
    + " ".join(["Bees are easier to keep than most people think."] * 10)
    + "\nKeywords:\n"
    + "".join(f"- keyword {n}\n" for n in range(7))
    + "Categories:\n- Books > Science & Math\n"
)
CHAPTER_ONE = (
    "# Chapter 1: The Hive\n\nBees live in **colonies** of [tens of thousands](http://x)[^1]."
)
CHAPTER_TWO = "# Chapter 2: The Site\n\nPut the hive where the morning sun reaches it."


class Tone(NarratorInterface):
    """A steady tone at a natural pace (0.4 seconds a word), optionally failing on one word."""

    def __init__(self, broken: str = "") -> None:
        self.broken = broken

    def narrate(self, text: str) -> Narration:
        if self.broken and self.broken in text:
            raise ApplicationError(
                code="ENGINE_DOWN", message="the engine stopped", http_status=503
            )
        count = int(len(text.split()) * 0.4 * RATE)
        samples = [0.2 * math.sin(2 * math.pi * 220 * i / RATE) for i in range(count)]
        return Narration(RATE, array("f", samples))


class Fast(NarratorInterface):
    """Far too quick to be speech: the gate refuses it for its pace."""

    def narrate(self, text: str) -> Narration:
        count = int(len(text.split()) * 0.01 * RATE)
        return Narration(RATE, array("f", [0.2] * max(count, 1)))


def world(
    **stored: str,
) -> tuple[AcxExportStageExecutor, InMemoryArtifactStore]:
    store = InMemoryArtifactStore()
    files = {
        "metadata.md": LISTING,
        "outline.md": OUTLINE,
        "manuscript/src/chapter_01.md": CHAPTER_ONE,
        "manuscript/src/chapter_02.md": CHAPTER_TWO,
        **stored,
    }
    for name, text in files.items():
        store.put("run-1", name, text.encode("utf-8"))
    return executor_for(store, None), store


def executor_for(
    store: InMemoryArtifactStore,
    narrator: NarratorInterface | None,
    author: str = "Adam Steinberger",
) -> AcxExportStageExecutor:
    return AcxExportStageExecutor(
        store,
        OutlineParser(),
        NarrationText(),
        MetadataParser(DashRewriter()),
        author,
        narrator,
        NarrationGate(),
    )


def run_for(stage: str = "audiobook") -> BookRun:
    return BookRun(
        run_id="run-1",
        brief=BookBrief(BookKind.NONFICTION, "bees", 5_000_000),
        plan=NonfictionRecipes().plan(),
        budget=Budget(cap=5_000_000, spent=0),
        stage=stage,
    )


def export(executor: AcxExportStageExecutor, attempt: int = 1):  # type: ignore[no-untyped-def]
    return asyncio.run(executor.execute(run_for(), attempt))


def text(store: InMemoryArtifactStore, name: str) -> str:
    data = store.get("run-1", name)
    assert data is not None
    return data.decode("utf-8")


def manifest(store: InMemoryArtifactStore) -> dict:  # type: ignore[type-arg]
    return json.loads(text(store, "acx-export.json"))


def wav_frames(store: InMemoryArtifactStore, name: str) -> int:
    data = store.get("run-1", name)
    assert data is not None
    with wave.open(io.BytesIO(data), "rb") as wav:
        return wav.getnframes()


def test_each_chapter_is_written_as_plain_speakable_text() -> None:
    executor, store = world()
    report = export(executor)
    assert report.issues == ()
    assert text(store, "acx/chapter_01.txt") == (
        "Chapter 1: The Hive\n\nBees live in colonies of tens of thousands.\n"
    )
    assert text(store, "acx/chapter_02.txt") == (
        "Chapter 2: The Site\n\nPut the hive where the morning sun reaches it.\n"
    )


def test_without_a_narrator_no_audio_is_made_and_the_manifest_says_why() -> None:
    executor, store = world()
    export(executor)
    data = manifest(store)
    assert data["audio"] == {
        "status": "not_narrated",
        "reason": "no narrator is configured (EI_NARRATOR)",
    }
    assert [name for name in store.names("run-1") if name.startswith("acx/audio/")] == []


def test_the_manifest_does_not_assume_virtual_voice_and_states_the_acx_rule() -> None:
    executor, store = world()
    export(executor)
    data = manifest(store)
    assert "applies for access" in data["virtual_voice"]
    assert "prohibits unauthorized text-to-speech" in data["acx_policy"]
    assert "narrator" not in data
    assert [(c["chapter"], c["file"]) for c in data["chapters"]] == [
        (1, "acx/chapter_01.txt"),
        (2, "acx/chapter_02.txt"),
    ]
    assert data["chapters"][0]["words"] == len(text(store, "acx/chapter_01.txt").split())


def test_with_a_narrator_every_part_gets_its_own_audio_file() -> None:
    store = InMemoryArtifactStore()
    for name, body in {
        "metadata.md": LISTING,
        "outline.md": OUTLINE,
        "manuscript/src/chapter_01.md": CHAPTER_ONE,
        "manuscript/src/chapter_02.md": CHAPTER_TWO,
    }.items():
        store.put("run-1", name, body.encode("utf-8"))
    report = export(executor_for(store, Tone()))
    assert report.issues == ()
    expected = [
        "acx/audio/chapter_01.wav",
        "acx/audio/chapter_02.wav",
        "acx/audio/opening-credits.wav",
        "acx/audio/closing-credits.wav",
        "acx/audio/retail-sample.wav",
    ]
    for name in expected:
        assert store.get("run-1", name) is not None, name
        assert wav_frames(store, name) > 0, name
    data = manifest(store)
    assert data["audio"]["status"] == "narrated"
    assert data["audio"]["ai_narration"] is True
    assert "synthetic voice" in data["audio"]["disclosure"]
    assert data["opening_credits_audio"]["file"] == "acx/audio/opening-credits.wav"
    assert data["retail_sample_audio"]["status"] == "narrated"
    assert data["chapters"][0]["audio"]["file"] == "acx/audio/chapter_01.wav"


def test_a_narrator_that_fails_on_a_part_is_reported_and_the_run_goes_on() -> None:
    store = InMemoryArtifactStore()
    for name, body in {
        "metadata.md": LISTING,
        "outline.md": OUTLINE,
        "manuscript/src/chapter_01.md": CHAPTER_ONE,
        "manuscript/src/chapter_02.md": CHAPTER_TWO,
    }.items():
        store.put("run-1", name, body.encode("utf-8"))
    report = export(executor_for(store, Tone(broken="Bees")))
    # "Bees" is in chapter 1 and so in the retail sample, which is cut from chapter 1: both parts fail, nothing stops.
    assert [issue.code for issue in report.issues] == ["ACX_AUDIO_FAILED", "ACX_AUDIO_FAILED"]
    assert all(not issue.blocking for issue in report.issues)
    assert {issue.detail.split(":")[0] for issue in report.issues} == {
        "chapter_01",
        "retail-sample",
    }
    assert store.get("run-1", "acx/audio/chapter_01.wav") is None
    assert store.get("run-1", "acx/audio/chapter_02.wav") is not None


def test_audio_the_gate_refuses_is_not_kept_and_is_reported() -> None:
    store = InMemoryArtifactStore()
    for name, body in {
        "metadata.md": LISTING,
        "outline.md": OUTLINE,
        "manuscript/src/chapter_01.md": CHAPTER_ONE,
        "manuscript/src/chapter_02.md": CHAPTER_TWO,
    }.items():
        store.put("run-1", name, body.encode("utf-8"))
    report = export(executor_for(store, Fast()))
    codes = {issue.code for issue in report.issues}
    assert codes == {"ACX_AUDIO_REJECTED"}
    assert all(not issue.blocking for issue in report.issues)
    assert not [name for name in store.names("run-1") if name.startswith("acx/audio/")]
    assert manifest(store)["chapters"][0]["audio"]["status"] == "rejected"


def test_a_redelivered_stage_keeps_the_text_and_the_audio_it_wrote() -> None:
    store = InMemoryArtifactStore()
    for name, body in {
        "metadata.md": LISTING,
        "outline.md": OUTLINE,
        "manuscript/src/chapter_01.md": CHAPTER_ONE,
        "manuscript/src/chapter_02.md": CHAPTER_TWO,
    }.items():
        store.put("run-1", name, body.encode("utf-8"))
    executor = executor_for(store, Tone())
    export(executor)
    before_text = store.get("run-1", "acx/chapter_01.txt")
    before_audio = store.get("run-1", "acx/audio/chapter_01.wav")
    export(executor, attempt=2)
    assert store.get("run-1", "acx/chapter_01.txt") == before_text
    assert store.get("run-1", "acx/audio/chapter_01.wav") == before_audio


def test_a_chapter_with_no_speakable_words_is_reported_and_does_not_stop_the_run() -> None:
    executor, store = world(**{"manuscript/src/chapter_02.md": "[^1]\n\n***"})
    report = export(executor)
    assert [issue.code for issue in report.issues] == ["ACX_EMPTY_CHAPTER"]
    assert not report.issues[0].blocking
    assert text(store, "acx/chapter_02.txt") == "\n"


def test_a_chapter_missing_from_the_manuscript_is_a_missing_input() -> None:
    store = InMemoryArtifactStore()
    store.put("run-1", "outline.md", OUTLINE.encode("utf-8"))
    store.put("run-1", "manuscript/src/chapter_01.md", CHAPTER_ONE.encode("utf-8"))
    with pytest.raises(ApplicationError) as error:
        asyncio.run(executor_for(store, None, author="").execute(run_for(), 1))
    assert error.value.code == "STAGE_INPUT_MISSING"


def test_the_credits_and_the_retail_sample_are_drafted_for_the_acx_uploads() -> None:
    executor, store = world()
    export(executor)
    assert text(store, "acx/opening-credits.txt") == "Hive Mind, written by Adam Steinberger.\n"
    assert (
        text(store, "acx/closing-credits.txt")
        == "You have been listening to Hive Mind, written by Adam Steinberger.\n"
    )
    sample = text(store, "acx/retail-sample.txt").split()
    assert (
        sample[:3] == ["Chapter", "1:", "The"]
        and len(sample) <= AcxExportStageExecutor.SAMPLE_WORDS
    )
    data = manifest(store)
    assert data["review_before_upload"] is True
    assert data["text"]["retail_sample_words"] == len(sample)


def test_without_an_author_the_credits_name_only_the_title() -> None:
    store = InMemoryArtifactStore()
    for name, body in {
        "metadata.md": LISTING,
        "outline.md": OUTLINE,
        "manuscript/src/chapter_01.md": CHAPTER_ONE,
        "manuscript/src/chapter_02.md": CHAPTER_TWO,
    }.items():
        store.put("run-1", name, body.encode("utf-8"))
    export(executor_for(store, None, author=""))
    assert text(store, "acx/opening-credits.txt") == "Hive Mind.\n"
