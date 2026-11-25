# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ReleaseSummary."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from engineering_influence.models.publishing.release_readiness_report import (
        ReleaseReadinessReport,
    )


class ReleaseSummaryInterface(ABC):
    """Status, findings, pricing, and format decisions, with the path of the full report."""

    __slots__ = ()

    @abstractmethod
    def of(self, report: ReleaseReadinessReport, report_path: str) -> dict[str, Any]:
        """The summary dictionary for a release-readiness report."""
