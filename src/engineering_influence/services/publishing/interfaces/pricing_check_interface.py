# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PricingCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from engineering_influence.models.publishing.release_readiness_report import (
        ReleaseReadinessReport,
    )


class PricingCheckInterface(ABC):
    """Validates volatile pricing assumptions and records the inputs used."""

    __slots__ = ()

    @abstractmethod
    def validate(
        self, report: ReleaseReadinessReport, release: dict[str, Any], severity: str, ref: str
    ) -> tuple[dict[str, Any], float | None, float | None, float | None]:
        """Return (pricing table, ebook, paperback, hardcover list prices)."""

    @abstractmethod
    def estimate(
        self,
        report: ReleaseReadinessReport,
        pricing: dict[str, Any],
        prices: tuple[float | None, float | None, float | None],
        page_count: int | None,
    ) -> None:
        """Record list prices, assumptions, and estimated print cost and royalties."""
