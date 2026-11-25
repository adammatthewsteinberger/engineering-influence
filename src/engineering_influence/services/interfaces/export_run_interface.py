# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ExportRun."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.export_summary import ExportSummary


class ExportRunInterface(ABC):
    """Puts what a run produced on disk, with the book laid out as a project."""

    __slots__ = ()

    @abstractmethod
    def export(self, run_id: str, target: Path) -> ExportSummary:
        """Write the run's artifacts under ``target``, or raise an ApplicationError saying why not."""
