# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The observability collaborators the REST interaction needs."""

from dataclasses import dataclass

from engineering_influence.interfaces.correlation_port import CorrelationPort
from engineering_influence.interfaces.metrics_port import MetricsPort
from engineering_influence.services.interfaces.readiness_probe_interface import (
    ReadinessProbeInterface,
)


@dataclass(frozen=True, slots=True)
class ApiObservability:
    """Readiness, metrics and correlation for the REST application."""

    readiness: ReadinessProbeInterface
    metrics: MetricsPort
    correlation: CorrelationPort
