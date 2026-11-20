# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for NavNcxCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents
    from engineering_influence.services.epub.toc_trees import TocTree


class NavNcxCheckInterface(ABC):
    """KDP rejects a book whose EPUB 3 contents and NCX disagree in any entry or level."""

    __slots__ = ()

    @abstractmethod
    def run(self, contents: EpubContents) -> tuple[list[str], TocTree | None]:
        """Return (problems, the NCX tree, or None when a document could not be parsed)."""
