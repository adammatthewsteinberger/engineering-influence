# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Readiness service contract."""

from abc import ABC, abstractmethod

from engineering_influence.contracts.readiness_report import ReadinessReport


class ReadinessProbeInterface(ABC):
    """Report whether the service can do useful work right now."""

    @abstractmethod
    def check(self) -> ReadinessReport:
        """Run every dependency check."""
