# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""RenderScreenplayStageExecutor: the script is typeset and kept as a PDF, a failed typesetting or an over-long film stops, and a film past three hours is only noted."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.screenplay_typesetter_interface import (
    ScreenplayTypesetterInterface,
)
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.screenplay_typeset import ScreenplayTypeset
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.render_screenplay_stage_executor import (
    RenderScreenplayStageExecutor,
)
from engineering_influence.services.screenplay_latex_source import ScreenplayLatexSource
from engineering_influence.services.screenplay_length import ScreenplayLength
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes

SCRIPT = (
    "Title: TEST FILM\n\nFADE IN:\n\nINT. ROOM - DAY\n\nScene plays.\n\nFADE OUT.\n\n>THE END<\n"
)


class Typesetter(ScreenplayTypesetterInterface):
    """Answers with the given pages and status, and keeps every LaTeX source it was given."""

    def __init__(self, pages: int = 120, status: int = 0, log: str = "") -> None:
        self.pages = pages
        self.status = status
        self.log = log
        self.sources: list[str] = []

    def typeset(self, tex: str) -> ScreenplayTypeset:
        self.sources.append(tex)
        if self.status != 0:
            return ScreenplayTypeset(status=self.status, pdf=b"", pages=0, log=self.log)
        return ScreenplayTypeset(status=0, pdf=b"%PDF-fake", pages=self.pages, log=self.log)


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000, title_hint="TEST FILM")
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def stage(store: InMemoryArtifactStore, typesetter: Typesetter) -> RenderScreenplayStageExecutor:
    return RenderScreenplayStageExecutor(
        store,
        ScreenplayLatexSource(FountainParser()),
        typesetter,
        ScreenplayLength(),
    )


def with_script(script: str = SCRIPT) -> InMemoryArtifactStore:
    store = InMemoryArtifactStore()
    store.put("run-1", "screenplay.fountain", script.encode("utf-8"))
    return store


def test_the_script_is_typeset_and_its_pdf_and_page_count_are_kept() -> None:
    store, typesetter = with_script(), Typesetter(pages=120)
    report = asyncio.run(stage(store, typesetter).execute(run(), 1))
    assert typesetter.sources[0].startswith("\\documentclass")
    assert store.get("run-1", "screenplay.pdf") == b"%PDF-fake"
    assert store.get("run-1", "render.md") == b"# Render\n\n- pages: 120\n"
    assert report.issues == ()


def test_a_script_that_does_not_typeset_stops_the_stage_with_the_log() -> None:
    typesetter = Typesetter(status=1, log="! Undefined control sequence.")
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(with_script(), typesetter).execute(run(), 1))
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert "LaTeX could not typeset the screenplay" in error.value.message
    assert "Undefined control sequence" in error.value.message


def test_a_film_over_the_ceiling_stops_the_stage() -> None:
    store = with_script()
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(store, Typesetter(pages=196)).execute(run(), 1))
    assert error.value.code == "STAGE_OUTPUT_INVALID"
    assert "196 pages is over the 195-page ceiling" in error.value.message
    assert store.get("run-1", "screenplay.pdf") is None


def test_a_film_past_three_hours_is_a_note_and_the_run_finishes() -> None:
    store = with_script()
    report = asyncio.run(stage(store, Typesetter(pages=185)).execute(run(), 1))
    assert store.get("run-1", "screenplay.pdf") == b"%PDF-fake"
    assert len(report.issues) == 1
    assert report.issues[0].code == "screenplay-length"
    assert report.issues[0].blocking is False
    assert "185 pages is past three hours" in report.issues[0].detail


def test_a_film_at_the_ceiling_is_within_the_limit() -> None:
    report = asyncio.run(stage(with_script(), Typesetter(pages=195)).execute(run(), 1))
    assert report.issues[0].code == "screenplay-length"


def test_a_missing_script_is_refused() -> None:
    with pytest.raises(ApplicationError) as error:
        asyncio.run(stage(InMemoryArtifactStore(), Typesetter()).execute(run(), 1))
    assert error.value.code == "STAGE_INPUT_MISSING"
