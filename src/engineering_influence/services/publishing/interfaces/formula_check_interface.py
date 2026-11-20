# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FormulaCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from engineering_influence.models.publishing.audit_report import AuditReport
    from engineering_influence.services.publishing.issue_recorder import IssueRecorder


class FormulaCheckInterface(ABC):
    """Warns when a formula such as 'the question is not' is overused."""

    __slots__ = ()

    @abstractmethod
    def run(
        self, report: AuditReport, recorder: IssueRecorder, quality: dict[str, Any], source: Path
    ) -> None:
        """Count each formula and warn above the threshold."""
