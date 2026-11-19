# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The facts of a finished PDF."""

from dataclasses import dataclass

from engineering_influence.models.publishing.interfaces.pdf_document_interface import (
    PdfDocumentInterface,
)
from engineering_influence.models.publishing.pdf_page import PdfPage


@dataclass(frozen=True, slots=True)
class PdfDocument(PdfDocumentInterface):
    """Every page of a PDF, and whether it carries bookmarks."""

    pages: tuple[PdfPage, ...]
    has_outline: bool
