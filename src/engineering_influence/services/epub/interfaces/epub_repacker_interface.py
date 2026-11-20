# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EpubRepacker."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.typesetting.book import Book


class EpubRepackerInterface(ABC):
    """Copies the EPUB with the finished OPF, nav, NCX, and XHTML."""

    __slots__ = ()

    @abstractmethod
    def zip_stamp(self, book: Book) -> tuple[int, int, int, int, int, int]:
        """A publication-year midnight: stable, and valid (ZIP cannot represent pre-1980)."""

    @abstractmethod
    def repack(self, epub: Path, book: Book, out: Path) -> None:
        """Write the finished EPUB to out."""
