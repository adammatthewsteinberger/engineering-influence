# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PageRasterizer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PageRasterizerInterface(ABC):
    """Uses poppler's pdftoppm when present, otherwise MuPDF's mutool."""

    __slots__ = ()

    @abstractmethod
    def command(self) -> str:
        """The renderer found on PATH."""

    @abstractmethod
    def clear_pages(self, directory: Path) -> None:
        """Remove only generated page images in the named QA directory."""

    @abstractmethod
    def rasterize(self, pdf: Path, pages_dir: Path, dpi: int, page_count: int) -> None:
        """Write page-0001.png ... into pages_dir; the pdf path must be absolute."""
