# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for AuditReport."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from engineering_influence.models.publishing.issue import Issue


class AuditReportInterface(ABC):
    """Inventory, thresholds, and issues for one configured manuscript."""

    __slots__ = ()

    @property
    @abstractmethod
    def errors(self) -> list[Issue]:
        """Blocking issues."""

    @abstractmethod
    def add(self, issue: Issue) -> None:
        """File an issue under warnings or blocking issues."""

    @abstractmethod
    def finish(self) -> None:
        """Set the overall status."""

    @abstractmethod
    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-ready dictionary."""
