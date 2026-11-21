# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RunSummaryV1."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
    from engineering_influence.models.book_run import BookRun


class RunSummaryV1Interface(ABC):
    """Version 1 of what the API and the CLI report about a book run."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def from_run(cls, run: BookRun, artifacts: list[str]) -> RunSummaryV1:
        """Describe a run and the artifacts it has stored."""
