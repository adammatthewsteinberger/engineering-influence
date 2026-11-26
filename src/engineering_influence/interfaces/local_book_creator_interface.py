# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: making a whole book from a brief in one process, and writing it out."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from engineering_influence.models.book_brief import BookBrief
    from engineering_influence.models.book_run import BookRun
    from engineering_influence.models.budget_plan import BudgetPlan
    from engineering_influence.models.export_summary import ExportSummary
    from engineering_influence.models.source_entry import SourceEntry


class LocalBookCreatorInterface(ABC):
    """Runs a book's whole plan locally and keeps the run in a folder, so it can be continued."""

    __slots__ = ()

    @abstractmethod
    def plan(self, brief: BookBrief) -> BudgetPlan | None:
        """The brief's cap set against what the book is expected to cost, or None when no model is priced."""

    @abstractmethod
    def start(
        self,
        brief: BookBrief,
        progress: Callable[[str], None],
        sources: tuple[SourceEntry, ...] = (),
        previous_lock: str | None = None,
    ) -> BookRun:
        """Run the brief's plan, with its source files, until the run finishes or stops."""

    @abstractmethod
    def resume(self, approve_spend: bool, progress: Callable[[str], None]) -> BookRun:
        """Continue the run this folder holds."""

    @abstractmethod
    def export(self, directory: Path) -> ExportSummary:
        """Write what the run produced to a new or empty folder."""

    @abstractmethod
    def close(self) -> None:
        """Release what the run opened."""
