# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for verifying a built EPUB."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.book import Book


class EpubVerifierInterface(ABC):
    """Check an EPUB against the Kindle rules and against itself."""

    __slots__ = ()

    @abstractmethod
    def verify(self, path: Path, book: Book) -> list[str]:
        """Every problem found; an empty list means the EPUB passes."""
