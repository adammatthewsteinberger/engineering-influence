# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Health checks derived from connection URLs."""

from urllib.parse import urlsplit

from engineering_influence.infrastructure.observability.tcp_health_check import TcpHealthCheck


class EndpointChecks:
    """Build a reachability check from a URL without ever exposing its credentials."""

    @staticmethod
    def tcp(name: str, url: str, default_port: int) -> TcpHealthCheck | None:
        """Check the URL's host and port; the rest of the URL (user, password) is dropped.

        A URL with no host, such as an embedded SQLite file, has nothing to connect to, so
        there is no check.
        """
        parts = urlsplit(url)
        if not parts.hostname:
            return None
        return TcpHealthCheck(name, parts.hostname, parts.port or default_port)
