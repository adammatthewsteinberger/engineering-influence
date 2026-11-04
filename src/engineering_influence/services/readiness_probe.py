# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Readiness service over dependency health checks."""

import logging

from engineering_influence.contracts.health_status import HealthStatus
from engineering_influence.contracts.readiness_report import ReadinessReport
from engineering_influence.interfaces.health_check_port import HealthCheckPort
from engineering_influence.services.interfaces.readiness_probe_interface import (
    ReadinessProbeInterface,
)

_LOGGER = logging.getLogger(__name__)


class ReadinessProbe(ReadinessProbeInterface):
    """Run every check; a check that raises counts as unhealthy, never as an error."""

    def __init__(self, checks: tuple[HealthCheckPort, ...]) -> None:
        self._checks = checks

    def check(self) -> ReadinessReport:
        """Return ready only when every check is healthy."""
        statuses = tuple(self._run(check) for check in self._checks)
        return ReadinessReport(ready=all(status.healthy for status in statuses), checks=statuses)

    @staticmethod
    def _run(check: HealthCheckPort) -> HealthStatus:
        try:
            status = check.check()
        except Exception as error:  # noqa: BLE001 - a broken check must not break the probe
            _LOGGER.warning(
                "health check raised", extra={"check": check.name, "error": type(error).__name__}
            )
            return HealthStatus(name=check.name, healthy=False, detail=type(error).__name__)
        if not status.healthy:
            _LOGGER.warning(
                "dependency unhealthy", extra={"check": status.name, "detail": status.detail}
            )
        return status
