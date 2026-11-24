# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for QualityReport."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.manuscript_build import ManuscriptBuild
    from engineering_influence.models.quality_issue import QualityIssue
    from engineering_influence.models.spend_summary import SpendSummary


class QualityReportInterface(ABC):
    """Writes the report of how well a run's book came out."""

    __slots__ = ()

    @abstractmethod
    def render(
        self,
        slug: str,
        issues: tuple[QualityIssue, ...],
        build: ManuscriptBuild,
        spend: SpendSummary | None = None,
    ) -> bytes:
        """The ``quality-report.json`` of the book, as bytes."""
