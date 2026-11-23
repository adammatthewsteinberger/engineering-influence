# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ListRuns."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class ListRunsInterface(ABC):
    """Lists the book runs the database holds."""

    __slots__ = ()

    @abstractmethod
    def runs(self) -> tuple[BookRun, ...]:
        """Every saved run, in the order the repository lists them."""
