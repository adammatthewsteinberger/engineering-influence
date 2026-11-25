# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookRun."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun
    from engineering_influence.models.budget import Budget
    from engineering_influence.models.quality_issue import QualityIssue


class BookRunInterface(ABC):
    """One run that turns a brief into a book, as an immutable value."""

    __slots__ = ()

    @abstractmethod
    def start(self) -> BookRun:
        """Mark a pending run as running, before its first stage begins."""

    @abstractmethod
    def advance(self) -> BookRun:
        """Move to the next stage, or complete the run after the last one."""

    @abstractmethod
    def park(self) -> BookRun:
        """Stop for lack of credit; ``resume`` continues from the same stage."""

    @abstractmethod
    def resume(self) -> BookRun:
        """Continue a parked run."""

    @abstractmethod
    def fail(self) -> BookRun:
        """End the run as failed."""

    @abstractmethod
    def cancel(self) -> BookRun:
        """End the run because someone asked it to stop."""

    @abstractmethod
    def with_budget(self, budget: Budget) -> BookRun:
        """The run with its budget replaced, after a reservation or a settlement."""

    @abstractmethod
    def with_issue(self, issue: QualityIssue) -> BookRun:
        """The run with one more recorded issue."""

    @abstractmethod
    def has_blocking_issue(self) -> bool:
        """True when any recorded issue should stop a release."""
