# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ManuscriptProject."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class ManuscriptProjectInterface(ABC):
    """Reads the assembled book of a run as the files of a project."""

    __slots__ = ()

    @abstractmethod
    async def load(self, run: BookRun) -> tuple[dict[str, bytes], str]:
        """The project's files, keyed by path (``books/slug.toml``, ``src/chapter_01.md``), and the book's slug."""
