# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Metrics port."""

from abc import ABC, abstractmethod


class MetricsPort(ABC):
    """Count events and expose what has been measured."""

    @abstractmethod
    def increment(self, name: str, amount: int = 1) -> None:
        """Add to a named counter."""

    @abstractmethod
    def counters(self) -> dict[str, int]:
        """Return every counter by name."""

    @abstractmethod
    def latencies(self) -> dict[str, dict[str, float]]:
        """Return latency statistics (count, errors, p50, p95, p99, max) by operation."""
