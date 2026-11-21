# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Orchestrates every PDF check for one built book."""

import tomllib
from pathlib import Path

from engineering_influence.interfaces.manuscript_source_interface import ManuscriptSourceInterface
from engineering_influence.interfaces.pdf_inspector_interface import PdfInspectorInterface
from engineering_influence.models.typesetting.text_policy import TextPolicy
from engineering_influence.models.typesetting.trim_size import TrimSize
from engineering_influence.services.publishing.contents_check import ContentsCheck
from engineering_influence.services.publishing.forbidden_content_check import ForbiddenContentCheck
from engineering_influence.services.publishing.interfaces.pdf_verifier_interface import (
    PdfVerifierInterface,
)
from engineering_influence.services.publishing.latex_log_check import LatexLogCheck
from engineering_influence.services.publishing.pdf_layout_check import PdfLayoutCheck
from engineering_influence.services.publishing.pdf_structure_check import PdfStructureCheck


class PdfVerifier(PdfVerifierInterface):
    """Checks an interior PDF against KDP print rules and against itself."""

    def __init__(self, pdfs: PdfInspectorInterface, files: ManuscriptSourceInterface) -> None:
        self._pdfs = pdfs
        self._files = files

    def verify(self, pdf_path: Path, config_path: Path, log_path: Path | None = None) -> list[str]:
        """Return every problem found; an empty list means the interior passes."""
        config = tomllib.loads(self._files.read_text(config_path))
        document = self._pdfs.inspect(pdf_path)
        trim = TrimSize.for_name(config.get("trim_size"))
        problems = PdfStructureCheck().run(document, trim)
        layout, texts, folios = PdfLayoutCheck().run(document.pages)
        problems += layout
        policy = TextPolicy.for_name(config.get("kind"))
        problems += ForbiddenContentCheck().run(texts, config.get("edition", ""), policy)
        contents, checked = ContentsCheck().run(texts, folios, config["title"])
        problems += contents
        if checked is None:
            return problems
        if log_path and self._files.exists(log_path):
            problems += LatexLogCheck().run(self._files.read_text(log_path, errors="replace"))
        return problems
