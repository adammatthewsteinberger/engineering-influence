# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FormatCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from engineering_influence.models.publishing.release_readiness_report import (
        ReleaseReadinessReport,
    )


class FormatCheckInterface(ABC):
    """Rejects a KDP hardcover that is too long or an unprovided external hardcover."""

    __slots__ = ()

    @abstractmethod
    def run(
        self,
        report: ReleaseReadinessReport,
        release: dict[str, Any],
        severity: str,
        ref: str,
        pdf_ref: str | None,
        hardcover_price: float | None,
    ) -> None:
        """Add findings and record the format decisions."""
