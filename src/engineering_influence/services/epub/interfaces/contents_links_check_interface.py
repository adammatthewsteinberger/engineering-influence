# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ContentsLinksCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.epub.epub_contents import EpubContents
    from engineering_influence.models.typesetting.book import Book


class ContentsLinksCheckInterface(ABC):
    """Counts the navigation entries and checks each target file, anchor, and heading id."""

    __slots__ = ()

    @abstractmethod
    def run(self, contents: EpubContents, book: Book) -> list[str]:
        """Return problems with the navigation document's contents links."""
