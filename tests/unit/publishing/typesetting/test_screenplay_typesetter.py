# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""LatexScreenplayTypesetter: the source is compiled in a scratch folder, its PDF and pages are read back, and a failure is returned with the log's tail."""

from pathlib import Path

import pytest

from engineering_influence.infrastructure.typesetting.latex_screenplay_typesetter import (
    LatexScreenplayTypesetter,
)
from engineering_influence.interfaces.latex_compiler_interface import LatexCompilerInterface
from engineering_influence.interfaces.pdf_inspector_interface import PdfInspectorInterface
from engineering_influence.models.publishing.pdf_document import PdfDocument
from engineering_influence.models.screenplay_typeset import ScreenplayTypeset


class Compiler(LatexCompilerInterface):
    """Writes a PDF into the folder unless told not to, and records what it was asked to build."""

    def __init__(self, status: int = 0, log: str = "built", write_pdf: bool = True) -> None:
        self.status = status
        self.log = log
        self.write_pdf = write_pdf
        self.calls: list[tuple[str, int, str]] = []

    def compile(self, workdir: Path, tex_name: str, source_date_epoch: int) -> tuple[int, str]:
        self.calls.append((tex_name, source_date_epoch, (workdir / tex_name).read_text("utf-8")))
        if self.write_pdf:
            (workdir / "screenplay.pdf").write_bytes(b"%PDF-fake")
        return self.status, self.log


class Inspector(PdfInspectorInterface):
    """Counts pages in the file, or reports the file missing as None."""

    def __init__(self, pages: int = 3) -> None:
        self.pages = pages

    def inspect(self, path: Path) -> PdfDocument:
        raise NotImplementedError

    def page_count(self, path: Path) -> int | None:
        return self.pages if path.exists() else None


def test_a_finished_typesetting_returns_its_pdf_and_pages() -> None:
    compiler = Compiler()
    result = LatexScreenplayTypesetter(compiler, Inspector(pages=3), 0).typeset(
        "\\documentclass{article}"
    )
    assert result == ScreenplayTypeset(status=0, pdf=b"%PDF-fake", pages=3, log="built")
    assert compiler.calls == [("screenplay.tex", 0, "\\documentclass{article}")]


def test_the_source_date_is_passed_through_so_the_pdf_date_is_pinned() -> None:
    compiler = Compiler()
    LatexScreenplayTypesetter(compiler, Inspector(), 1_700_000_000).typeset("x")
    assert compiler.calls[0][1] == 1_700_000_000


def test_a_failed_compile_is_returned_with_its_status_and_the_log_tail() -> None:
    log = "\n".join(f"line {n}" for n in range(1, 31))
    result = LatexScreenplayTypesetter(Compiler(status=12, log=log), Inspector()).typeset("x")
    assert result.status == 12
    assert result.pdf == b"" and result.pages == 0
    assert result.log.splitlines()[0] == "line 11"
    assert result.log.splitlines()[-1] == "line 30"
    assert len(result.log.splitlines()) == 20


def test_a_compile_that_leaves_no_pdf_is_a_failure_with_status_one() -> None:
    result = LatexScreenplayTypesetter(Compiler(status=0, write_pdf=False), Inspector()).typeset(
        "x"
    )
    assert result.status == 1
    assert result.pages == 0


def test_a_pdf_with_no_pages_is_a_failure() -> None:
    result = LatexScreenplayTypesetter(Compiler(), Inspector(pages=0)).typeset("x")
    assert result.status == 1


def test_a_finished_typesetting_with_no_pages_cannot_be_a_result() -> None:
    with pytest.raises(ValueError, match="at least one page"):
        ScreenplayTypeset(status=0, pdf=b"", pages=0, log="")
