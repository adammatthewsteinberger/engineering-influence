# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CancelRun."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class CancelRunInterface(ABC):
    """Stop a run for good."""

    __slots__ = ()

    @abstractmethod
    def cancel(self, run_id: str) -> BookRun:
        """Mark the run cancelled and return it."""
