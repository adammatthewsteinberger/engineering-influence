# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for AuditReportText."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.publishing.audit_report import AuditReport
    from engineering_influence.models.publishing.release_readiness_report import (
        ReleaseReadinessReport,
    )


class AuditReportTextInterface(ABC):
    """The lines a person reads after an audit."""

    __slots__ = ()

    @abstractmethod
    def manuscript(self, report: AuditReport) -> str:
        """Counts, every issue and warning with its location, and a pass line."""

    @abstractmethod
    def release(self, report: ReleaseReadinessReport) -> str:
        """Release-readiness status and each finding."""
