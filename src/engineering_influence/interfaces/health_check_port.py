# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Health check port."""

from abc import ABC, abstractmethod

from engineering_influence.contracts.health_status import HealthStatus


class HealthCheckPort(ABC):
    """Check one dependency the service cannot work without."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the stable dependency name used in reports and metrics."""

    @abstractmethod
    def check(self) -> HealthStatus:
        """Return the dependency's status; this must be quick and must not raise."""
