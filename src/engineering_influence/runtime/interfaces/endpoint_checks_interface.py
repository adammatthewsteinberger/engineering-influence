# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EndpointChecks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.infrastructure.observability.tcp_health_check import TcpHealthCheck


class EndpointChecksInterface(ABC):
    """Build a reachability check from a URL without ever exposing its credentials."""

    __slots__ = ()

    @staticmethod
    @abstractmethod
    def tcp(name: str, url: str, default_port: int) -> TcpHealthCheck | None:
        """Check the URL's host and port; the rest of the URL (user, password) is dropped."""
