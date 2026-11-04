# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Validated process settings."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Everything a process needs from its environment.

    ``database_url`` and ``rabbitmq_url`` carry credentials, so they are never logged.
    """

    database_url: str
    rabbitmq_url: str
    queue_name: str = "engineering-influence.jobs"
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    rate_burst: float = 30.0
    rate_per_second: float = 10.0

    def __repr__(self) -> str:
        return (
            f"AppSettings(queue_name={self.queue_name!r}, log_level={self.log_level!r}, "
            f"host={self.host!r}, port={self.port})"
        )
