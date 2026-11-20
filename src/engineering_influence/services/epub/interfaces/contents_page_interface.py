# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ContentsPage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from engineering_influence.models.typesetting.book import Book
    from engineering_influence.services.epub.contents_page import Entries


class ContentsPageInterface(ABC):
    """Turns TeX4ht's contents page into plain linked divs, in the Kindle Publishing form."""

    __slots__ = ()

    @abstractmethod
    def heading_target(self, href: str, read: Callable[[str], str]) -> str:
        """Point a contents link at its chapter's heading."""

    @abstractmethod
    def html_toc(self, entries: Entries) -> str:
        """One linked <div> per entry, chapters indented by a CSS class, no list markup."""

    @abstractmethod
    def finish(self, page: str, book: Book, read: Callable[[str], str]) -> tuple[str, Entries]:
        """Return (the plain contents page, its entries)."""
