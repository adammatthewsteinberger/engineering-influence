# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for OpfEditor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.book import Book


class OpfEditorInterface(ABC):
    """Adds store metadata, the separate nav document, the guide, and the cover."""

    __slots__ = ()

    @abstractmethod
    def finish(self, opf: str, book: Book) -> str:
        """Add store metadata and normalize every publication date to the release year."""

    @abstractmethod
    def move_nav(self, opf: str, toc_page: str) -> str:
        """Make nav.xhtml the navigation document, outside the spine; the contents page stays."""

    @abstractmethod
    def add_guide(self, opf: str, nav_href: str, start_href: str) -> str:
        """The EPUB 2 guide, which older Kindle conversions still read for the same two places."""

    @abstractmethod
    def add_cover(self, opf: str) -> str:
        """Declare the cover both ways the Kindle Publishing Guidelines accept."""
