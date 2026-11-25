# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ThresholdCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from engineering_influence.models.publishing.audit_report import AuditReport
    from engineering_influence.services.publishing.issue_recorder import IssueRecorder


class ThresholdCheckInterface(ABC):
    """Records counts and thresholds, then reports the ones the manuscript misses."""

    __slots__ = ()

    @abstractmethod
    def run(
        self,
        report: AuditReport,
        recorder: IssueRecorder,
        quality: dict[str, Any],
        source: Path,
        source_count: int,
        ignored_count: int,
    ) -> None:
        """Fill report counts and thresholds and record threshold issues."""
