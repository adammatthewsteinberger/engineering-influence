# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Orchestrates every PDF check for one built book."""

import tomllib
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from engineering_influence.publishing.contents_check import ContentsCheck
from engineering_influence.publishing.forbidden_content_check import ForbiddenContentCheck
from engineering_influence.publishing.latex_log_check import LatexLogCheck
from engineering_influence.publishing.pdf_layout_check import PdfLayoutCheck
from engineering_influence.publishing.pdf_structure_check import PdfStructureCheck


class PdfVerifier:
    """Checks an interior PDF against KDP print rules and against itself."""

    def verify(self, pdf_path: Path, config_path: Path, log_path: Path | None = None) -> list[str]:
        """Return every problem found; an empty list means the interior passes."""
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        problems = PdfStructureCheck().run(PdfReader(str(pdf_path)))
        with pdfplumber.open(str(pdf_path)) as pdf:
            layout, texts, folios = PdfLayoutCheck().run(list(pdf.pages))
        problems += layout
        problems += ForbiddenContentCheck().run(texts, config.get("edition", ""))
        contents, checked = ContentsCheck().run(texts, folios, config["title"])
        problems += contents
        if checked is None:
            return problems
        if log_path and log_path.exists():
            problems += LatexLogCheck().run(log_path.read_text(errors="replace"))
        return problems
