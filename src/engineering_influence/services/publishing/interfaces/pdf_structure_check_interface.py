# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PdfStructureCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.publishing.pdf_document import PdfDocument


class PdfStructureCheckInterface(ABC):
    """Applies the KDP structure rules to the facts of a finished PDF."""

    __slots__ = ()

    @abstractmethod
    def run(self, document: PdfDocument) -> list[str]:
        """Return a problem for each structural violation."""
