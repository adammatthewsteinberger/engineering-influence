# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RunManagement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class RunManagementInterface(ABC):
    """Lists, resumes and cancels book runs for the transports that reach them over the network."""

    __slots__ = ()

    @abstractmethod
    def runs(self) -> tuple[BookRun, ...]:
        """Every saved run."""

    @abstractmethod
    def resume(self, run_id: str) -> BookRun:
        """Un-park a parked run and queue its current stage."""

    @abstractmethod
    def cancel(self, run_id: str) -> BookRun:
        """Stop a run for good."""
