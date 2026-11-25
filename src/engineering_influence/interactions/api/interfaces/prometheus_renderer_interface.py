# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PrometheusRenderer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.contracts.readiness_report import ReadinessReport


class PrometheusRendererInterface(ABC):
    """Render the text format (version 0.0.4) that Prometheus and compatible agents scrape."""

    __slots__ = ()

    @abstractmethod
    def render(
        self,
        counters: dict[str, int],
        latencies: dict[str, dict[str, float]],
        readiness: ReadinessReport | None,
    ) -> str:
        """Return the exposition text; names are prefixed and sanitised, labels escaped."""
