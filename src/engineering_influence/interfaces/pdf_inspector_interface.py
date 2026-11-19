# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for reading the facts of a finished PDF."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.publishing.pdf_document import PdfDocument


class PdfInspectorInterface(ABC):
    """Turn a PDF file into plain facts, so the checks never touch a PDF library."""

    __slots__ = ()

    @abstractmethod
    def inspect(self, path: Path) -> PdfDocument:
        """Read every page of the PDF."""

    @abstractmethod
    def page_count(self, path: Path) -> int | None:
        """The number of pages, or None when the file does not exist."""
