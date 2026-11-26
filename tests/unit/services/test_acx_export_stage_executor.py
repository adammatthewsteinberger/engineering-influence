# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""AcxExportStageExecutor: each chapter as speakable plain text, and a manifest that names Virtual Voice as the narrator."""

import asyncio
import json

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.services.acx_export_stage_executor import AcxExportStageExecutor
from engineering_influence.services.dash_rewriter import DashRewriter
from engineering_influence.services.metadata_parser import MetadataParser
from engineering_influence.services.narration_text import NarrationText
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.outline_parser import OutlineParser

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


def world(**stored: str) -> tuple[AcxExportStageExecutor, InMemoryArtifactStore]:
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
    return AcxExportStageExecutor(
        store, OutlineParser(), NarrationText(), MetadataParser(DashRewriter()), "Adam Steinberger"
    ), store


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


def test_the_manifest_names_virtual_voice_and_lists_each_chapter() -> None:
    executor, store = world()
    export(executor)
    manifest = json.loads(text(store, "acx-export.json"))
    assert manifest["status"] == "exported"
    assert manifest["narrator"] == AcxExportStageExecutor.NARRATOR
    assert [(c["chapter"], c["file"]) for c in manifest["chapters"]] == [
        (1, "acx/chapter_01.txt"),
        (2, "acx/chapter_02.txt"),
    ]
    assert manifest["chapters"][0]["words"] == len(text(store, "acx/chapter_01.txt").split())


def test_a_chapter_with_no_speakable_words_is_reported_and_does_not_stop_the_run() -> None:
    executor, store = world(**{"manuscript/src/chapter_02.md": "[^1]\n\n***"})
    report = export(executor)
    assert [issue.code for issue in report.issues] == ["ACX_EMPTY_CHAPTER"]
    assert not report.issues[0].blocking
    assert text(store, "acx/chapter_02.txt") == "\n"


def test_a_redelivered_stage_keeps_the_files_it_wrote() -> None:
    executor, store = world()
    export(executor)
    before = store.get("run-1", "acx/chapter_01.txt")
    export(executor, attempt=2)
    assert store.get("run-1", "acx/chapter_01.txt") == before


def test_a_chapter_missing_from_the_manuscript_is_a_missing_input() -> None:
    _executor, _ = world()
    store = InMemoryArtifactStore()
    store.put("run-1", "outline.md", OUTLINE.encode("utf-8"))
    store.put("run-1", "manuscript/src/chapter_01.md", CHAPTER_ONE.encode("utf-8"))
    with pytest.raises(ApplicationError) as error:
        asyncio.run(
            AcxExportStageExecutor(
                store, OutlineParser(), NarrationText(), MetadataParser(DashRewriter()), ""
            ).execute(run_for(), 1)
        )
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
    manifest = json.loads(text(store, "acx-export.json"))
    assert manifest["review_before_upload"] is True
    assert manifest["retail_sample_words"] == len(sample)


def test_without_an_author_the_credits_name_only_the_title() -> None:
    store = InMemoryArtifactStore()
    for name, body in {
        "metadata.md": LISTING,
        "outline.md": OUTLINE,
        "manuscript/src/chapter_01.md": CHAPTER_ONE,
        "manuscript/src/chapter_02.md": CHAPTER_TWO,
    }.items():
        store.put("run-1", name, body.encode("utf-8"))
    executor = AcxExportStageExecutor(
        store, OutlineParser(), NarrationText(), MetadataParser(DashRewriter()), ""
    )
    asyncio.run(executor.execute(run_for(), 1))
    assert text(store, "acx/opening-credits.txt") == "Hive Mind.\n"
