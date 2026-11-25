# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ChapterLoader."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.typesetting.chapter import Chapter


class ChapterLoaderInterface(ABC):
    """Parses the title, epigraph, and body; refuses unfinished markers when strict."""

    __slots__ = ()

    @abstractmethod
    def load(self, path: Path, kind: str, style: str, short: str | None) -> Chapter:
        """Read the file at path."""
