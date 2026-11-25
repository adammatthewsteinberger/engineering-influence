# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PdfLayoutCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from engineering_influence.models.publishing.pdf_page import PdfPage


class PdfLayoutCheckInterface(ABC):
    """Walks the pages of a PDF and reports margin and blank-page violations."""

    __slots__ = ()

    @abstractmethod
    def run(self, pages: Sequence[PdfPage]) -> tuple[list[str], list[str], list[str | None]]:
        """Return (problems, page texts, printed folios)."""
