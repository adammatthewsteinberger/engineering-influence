# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CategoryCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engineering_influence.models.publishing.release_readiness_report import (
        ReleaseReadinessReport,
    )


class CategoryCheckInterface(ABC):
    """Checks the browse categories a book declares for its KDP listing."""

    __slots__ = ()

    @abstractmethod
    def run(
        self, report: ReleaseReadinessReport, release: dict[str, Any], severity: str, ref: str
    ) -> None:
        """Add findings and record the categories."""
