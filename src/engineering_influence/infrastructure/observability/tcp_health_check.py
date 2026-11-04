# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reachability check for a TCP dependency such as Postgres or RabbitMQ."""

import socket

from engineering_influence.contracts.health_status import HealthStatus
from engineering_influence.interfaces.health_check_port import HealthCheckPort


class TcpHealthCheck(HealthCheckPort):
    """Healthy when a TCP connection to the host and port opens within the timeout."""

    def __init__(self, name: str, host: str, port: int, timeout_seconds: float = 2.0) -> None:
        self._name = name
        self._host = host
        self._port = port
        self._timeout = timeout_seconds

    @property
    def name(self) -> str:
        """Return the dependency name."""
        return self._name

    def check(self) -> HealthStatus:
        """Open and close a connection; report only the failure class, never the address."""
        try:
            with socket.create_connection((self._host, self._port), timeout=self._timeout):
                return HealthStatus(name=self._name, healthy=True)
        except OSError as error:
            return HealthStatus(name=self._name, healthy=False, detail=type(error).__name__)
