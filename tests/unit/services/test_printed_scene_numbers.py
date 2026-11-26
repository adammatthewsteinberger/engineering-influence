# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The locked scene numbers print: a heading's number is split off, the PDF puts it at the right margin, the EPUB floats it,
and both outputs use the locked script when the lock stage stored one."""

import asyncio

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
from engineering_influence.services.screenplay_latex_source import ScreenplayLatexSource
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes

PLAIN = "Title: T\n\nINT. ROOM - DAY\n\nIt plays.\n"
NUMBERED = "Title: T\n\nINT. ROOM - DAY #42A#\n\nIt plays.\n"


def run() -> BookRun:
    brief = BookBrief(BookKind.SCREENPLAY, "a film", 5_000_000, title_hint="T")
    return BookRun(
        run_id="run-1", brief=brief, plan=ScreenplayRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def test_a_heading_number_is_split_off_and_a_heading_without_one_is_left_alone() -> None:
    parser = FountainParser()
    assert parser.split_scene_number("INT. ROOM - DAY #42A#") == ("INT. ROOM - DAY", "42A")
    assert parser.split_scene_number("INT. ROOM - DAY") == ("INT. ROOM - DAY", None)


def test_the_pdf_heading_puts_the_number_at_the_right_margin() -> None:
    tex = ScreenplayLatexSource(FountainParser()).render(NUMBERED)
    assert "INT. ROOM - DAY\\hfill 42A" in tex
    assert "#42A#" not in tex


def test_a_pdf_heading_without_a_number_has_no_margin_number() -> None:
    assert "\\hfill" not in ScreenplayLatexSource(FountainParser()).render(PLAIN)


def test_the_epub_heading_floats_its_number_and_the_stylesheet_says_so() -> None:
    entries = {
        name: data for name, data, _ in ScreenplayEpubPackage(FountainParser()).entries(NUMBERED)
    }
    page = entries["OEBPS/screenplay.xhtml"].decode("utf-8")
    assert '<p class="heading">INT. ROOM - DAY<span class="scene-number">42A</span></p>' in page
    assert b".scene-number { float: right; }" in entries["OEBPS/style.css"]


def test_the_render_stage_typesets_the_locked_script_when_there_is_one() -> None:
    from engineering_influence.interfaces.screenplay_typesetter_interface import (
        ScreenplayTypesetterInterface,
    )
    from engineering_influence.models.screenplay_typeset import ScreenplayTypeset
    from engineering_influence.services.render_screenplay_stage_executor import (
        RenderScreenplayStageExecutor,
    )
    from engineering_influence.services.screenplay_length import ScreenplayLength

    class Recording(ScreenplayTypesetterInterface):
        def __init__(self) -> None:
            self.sources: list[str] = []

        def typeset(self, tex: str) -> ScreenplayTypeset:
            self.sources.append(tex)
            return ScreenplayTypeset(status=0, pdf=b"%PDF", pages=10, log="")

    store = InMemoryArtifactStore()
    store.put("run-1", "screenplay.fountain", PLAIN.encode("utf-8"))
    store.put("run-1", "shooting_script.fountain", NUMBERED.encode("utf-8"))
    typesetter = Recording()
    stage = RenderScreenplayStageExecutor(
        store, ScreenplayLatexSource(FountainParser()), typesetter, ScreenplayLength()
    )
    asyncio.run(stage.execute(run(), 1))
    assert "\\hfill 42A" in typesetter.sources[0]


def test_the_render_stage_falls_back_to_the_plain_script_without_a_lock() -> None:
    from engineering_influence.interfaces.screenplay_typesetter_interface import (
        ScreenplayTypesetterInterface,
    )
    from engineering_influence.models.screenplay_typeset import ScreenplayTypeset
    from engineering_influence.services.render_screenplay_stage_executor import (
        RenderScreenplayStageExecutor,
    )
    from engineering_influence.services.screenplay_length import ScreenplayLength

    class Recording(ScreenplayTypesetterInterface):
        def __init__(self) -> None:
            self.sources: list[str] = []

        def typeset(self, tex: str) -> ScreenplayTypeset:
            self.sources.append(tex)
            return ScreenplayTypeset(status=0, pdf=b"%PDF", pages=10, log="")

    store = InMemoryArtifactStore()
    store.put("run-1", "screenplay.fountain", PLAIN.encode("utf-8"))
    typesetter = Recording()
    stage = RenderScreenplayStageExecutor(
        store, ScreenplayLatexSource(FountainParser()), typesetter, ScreenplayLength()
    )
    asyncio.run(stage.execute(run(), 1))
    assert "\\hfill" not in typesetter.sources[0]


def test_the_epub_stage_packages_the_locked_script_when_there_is_one() -> None:
    class Writer(ScreenplayEpubWriterInterface):
        def __init__(self) -> None:
            self.entries: tuple[tuple[str, bytes, bool], ...] = ()

        def write(self, entries: tuple[tuple[str, bytes, bool], ...]) -> tuple[bytes, list[str]]:
            self.entries = entries
            return b"epub", []

    store = InMemoryArtifactStore()
    store.put("run-1", "screenplay.fountain", PLAIN.encode("utf-8"))
    store.put("run-1", "shooting_script.fountain", NUMBERED.encode("utf-8"))
    writer = Writer()
    stage = BuildScreenplayEpubStageExecutor(store, ScreenplayEpubPackage(FountainParser()), writer)
    asyncio.run(stage.execute(run(), 1))
    page = next(data for name, data, _ in writer.entries if name == "OEBPS/screenplay.xhtml")
    assert b"scene-number" in page
