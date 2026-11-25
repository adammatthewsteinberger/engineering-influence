# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FolioReader."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.publishing.pdf_page import PdfPage


class FolioReaderInterface(ABC):
    """Finds the folio in the running head or the opener footer."""

    __slots__ = ()

    @abstractmethod
    def read(self, page: PdfPage) -> str | None:
        """Return the printed folio, or None when the page prints none."""
