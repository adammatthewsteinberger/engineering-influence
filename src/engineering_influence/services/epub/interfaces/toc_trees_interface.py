# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TocTrees."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.services.epub.toc_trees import TocTree


class TocTreesInterface(ABC):
    """Nested (label, href, children) lists, so the two contents can be compared."""

    __slots__ = ()

    @abstractmethod
    def from_nav(self, nav: str) -> TocTree:
        """The EPUB 3 contents of a navigation document."""

    @abstractmethod
    def from_ncx(self, ncx: str) -> TocTree:
        """The NCX navMap."""
