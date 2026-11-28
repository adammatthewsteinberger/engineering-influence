# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""AudiobookOutlineStageExecutor: each finished chapter is stored as a chapter, and the outline built from them is one the
outline parser reads; a chapter with no text stops the stage."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.services.audiobook_outline_stage_executor import (
    AudiobookOutlineStageExecutor,
)
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.outline_parser import OutlineParser

ONE = "# The Walls\n\nThe station held its breath. Nobody spoke.\n\nThe air was thin. The crew counted it.\n"
TWO = "# Clean Signal\n\nA signal came in at dawn. It repeated.\n"


def run() -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "a book", 1_000_000)
    return BookRun(
        run_id="run-1", brief=brief, plan=CreateRun.AUDIOBOOK_PLAN, budget=Budget(cap=1_000_000)
    )


def store(*chapters: str) -> InMemoryArtifactStore:
    s = InMemoryArtifactStore()
    for number, text in enumerate(chapters, 1):
        s.put("run-1", f"source/{number:03d}.md", text.encode("utf-8"))
    return s


def text(s: InMemoryArtifactStore, name: str) -> str:
    data = s.get("run-1", name)
    assert data is not None
    return data.decode("utf-8")


def test_each_chapter_is_stored_and_the_outline_parses_to_the_same_chapters() -> None:
    s = store(ONE, TWO)
    asyncio.run(AudiobookOutlineStageExecutor(s).execute(run(), 1))
    assert text(s, "manuscript/src/chapter_01.md") == ONE
    assert text(s, "manuscript/src/chapter_02.md") == TWO
    outline = OutlineParser().parse(text(s, "outline.md"))
    assert [chapter.number for chapter in outline.chapters] == [1, 2]
    assert outline.chapters[0].purpose == "The station held its breath."
    assert outline.chapters[0].beats[0].startswith("The station held its breath")


def test_a_run_with_no_chapters_is_refused() -> None:
    with pytest.raises(ApplicationError) as refused:
        asyncio.run(AudiobookOutlineStageExecutor(InMemoryArtifactStore()).execute(run(), 1))
    assert refused.value.code == "STAGE_INPUT_MISSING"


def test_a_chapter_with_no_text_stops_the_stage() -> None:
    with pytest.raises(ApplicationError) as refused:
        asyncio.run(AudiobookOutlineStageExecutor(store("# Only a heading\n")).execute(run(), 1))
    assert "has no text to narrate" in refused.value.message
