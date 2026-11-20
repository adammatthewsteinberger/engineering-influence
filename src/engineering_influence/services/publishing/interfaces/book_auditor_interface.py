# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookAuditor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.publishing.audit_report import AuditReport


class BookAuditorInterface(ABC):
    """Source-oriented gates: inventory, openings, scaffolding, depth, and apparatus."""

    __slots__ = ()

    @abstractmethod
    def audit(self, config_path: Path) -> AuditReport:
        """Return the audit report for one book config."""
