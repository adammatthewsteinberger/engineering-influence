# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ResumeRun."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class ResumeRunInterface(ABC):
    """Get a parked or stalled run moving again."""

    __slots__ = ()

    @abstractmethod
    def resume(self, run_id: str) -> BookRun:
        """Un-park the run if it is parked, queue its current stage, and return it."""
