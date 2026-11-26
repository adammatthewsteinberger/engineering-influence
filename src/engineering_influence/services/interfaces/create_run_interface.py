# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CreateRun."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_brief import BookBrief
    from engineering_influence.models.book_run import BookRun
    from engineering_influence.models.source_entry import SourceEntry


class CreateRunInterface(ABC):
    """Starts a book run from a brief."""

    __slots__ = ()

    @abstractmethod
    def create(
        self,
        brief: BookBrief,
        sources: tuple[SourceEntry, ...] = (),
        previous_lock: str | None = None,
    ) -> BookRun:
        """Save a new pending run for the brief and queue its first stage; return the run."""
