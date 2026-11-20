# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ChapterTex."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.typesetting.chapter import Chapter


class ChapterTexInterface(ABC):
    """Heading, table-of-contents entry, running head, epigraph, and body."""

    __slots__ = ()

    @abstractmethod
    def render(self, chapter: Chapter, number_chapters: bool = True) -> str:
        """Return the chapter's LaTeX."""
