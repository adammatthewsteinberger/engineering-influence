# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""BuildScreenplayEpubStageExecutor: the EPUB is stored when epubcheck accepts it, and refused, with its first findings, when it does not."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.screenplay_epub_writer_interface import (
    ScreenplayEpubWriterInterface,
)
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.services.build_screenplay_epub_stage_executor import (
    BuildScreenplayEpubStageExecutor,
)
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.screenplay_epub_package import ScreenplayEpubPackage
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes


class Writer(ScreenplayEpubWriterInterface):
    """Returns the given bytes and findings, and keeps the members it was asked to write."""

    def __init__(self, problems: tuple[str, ...] = ()) -> None:
        self.problems = problems
        self.written: list[tuple[str, bytes, bool]] = []

    def write(self, entries: tuple[tuple[str, bytes, bool], ...]) -> tuple[bytes, tuple[str, ...]]:
        self.written = list(entries)
        return b"EPUB-BYTES", self.problems


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000, title_hint="TEST FILM")
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def with_script() -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.put("run-1", "screenplay.fountain", b"Title: TEST FILM\n\nFADE IN:\n\nINT. ROOM - DAY\n")
    return store


def stage(store: InMemoryArtifactStore, writer: Writer) -> BuildScreenplayEpubStageExecutor:
    return BuildScreenplayEpubStageExecutor(store, ScreenplayEpubPackage(FountainParser()), writer)


def test_a_valid_epub_is_stored_and_its_members_are_the_package() -> None:
    store, writer = with_script(), Writer()
    asyncio.run(stage(store, writer).execute(run(), 1))
    assert store.get("run-1", "screenplay.epub") == b"EPUB-BYTES"
    assert writer.written[0][0] == "mimetype"


def test_an_epub_epubcheck_rejects_is_not_stored() -> None:
    store = with_script()
    writer = Writer(problems=("ERROR: bad markup", "WARNING: unused file"))
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(store, writer).execute(run(), 1))
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert (
        error.value.message
        == "the screenplay EPUB fails epubcheck: ERROR: bad markup; WARNING: unused file"
    )
    assert store.get("run-1", "screenplay.epub") is None


def test_only_the_first_five_findings_are_named() -> None:
    writer = Writer(problems=tuple(f"ERROR: {n}" for n in range(1, 9)))
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(with_script(), writer).execute(run(), 1))
    assert error.value.message.count("ERROR") == 5


def test_a_missing_script_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(InMemoryArtifactStore(), Writer()).execute(run(), 1))
    assert error.value.code == "STAGE_INPUT_MISSING"
