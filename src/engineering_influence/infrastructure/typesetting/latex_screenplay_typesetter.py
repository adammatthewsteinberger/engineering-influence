# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Typesets a screenplay with LuaLaTeX in a scratch folder, and reads back its PDF and page count."""

import tempfile
from pathlib import Path
from typing import ClassVar

from engineering_influence.interfaces.latex_compiler_interface import LatexCompilerInterface
from engineering_influence.interfaces.pdf_inspector_interface import PdfInspectorInterface
from engineering_influence.interfaces.screenplay_typesetter_interface import (
    ScreenplayTypesetterInterface,
)
from engineering_influence.models.screenplay_typeset import ScreenplayTypeset


class LatexScreenplayTypesetter(ScreenplayTypesetterInterface):
    """The source goes into a scratch folder that is removed afterwards, so nothing is left behind by a failed run.

    A typesetting that fails (LaTeX exits non-zero, or leaves no PDF) is returned with its status and the last lines of
    its log, not raised: the stage decides what a failure means for the run. ``source_date_epoch`` pins the PDF's date,
    so typesetting the same script twice gives the same file.
    """

    TEX_NAME: ClassVar[str] = "screenplay.tex"
    PDF_NAME: ClassVar[str] = "screenplay.pdf"
    LOG_LINES: ClassVar[int] = 20

    def __init__(
        self,
        compiler: LatexCompilerInterface,
        inspector: PdfInspectorInterface,
        source_date_epoch: int = 0,
    ) -> None:
        """Remember the compiler, the PDF inspector and the source date."""
        self._compiler = compiler
        self._inspector = inspector
        self._epoch = source_date_epoch

    def typeset(self, tex: str) -> ScreenplayTypeset:
        """The typeset PDF with its page count, or the failure with the log's tail."""
        with tempfile.TemporaryDirectory(prefix="screenplay-") as scratch:
            workdir = Path(scratch)
            (workdir / self.TEX_NAME).write_text(tex, encoding="utf-8")
            status, log = self._compiler.compile(workdir, self.TEX_NAME, self._epoch)
            pdf = workdir / self.PDF_NAME
            pages = self._inspector.page_count(pdf)
            tail = "\n".join(log.splitlines()[-self.LOG_LINES :])
            if status != 0 or pages is None or pages < 1:
                return ScreenplayTypeset(status=status or 1, pdf=b"", pages=0, log=tail)
            facts = self._inspector.inspect(pdf).pages
            return ScreenplayTypeset(
                status=0, pdf=pdf.read_bytes(), pages=pages, log=tail, facts=facts
            )
