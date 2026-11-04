# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Read process settings from the environment, failing closed on anything missing."""

import os
from collections.abc import Mapping

from engineering_influence.interfaces.secret_provider_port import SecretProviderPort
from engineering_influence.runtime.app_settings import AppSettings

_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class EnvironmentSettingsLoader:
    """``EI_DATABASE_URL`` and ``EI_RABBITMQ_URL`` are required; the rest have safe defaults.

    The API binds to loopback unless ``EI_HOST`` says otherwise, so a bare run is never
    reachable from the network by accident.
    """

    def __init__(
        self, secrets: SecretProviderPort, environ: Mapping[str, str] | None = None
    ) -> None:
        self._secrets = secrets
        self._environ = os.environ if environ is None else environ

    def load(self) -> AppSettings:
        """Return validated settings or raise with the name of the offending variable."""
        level = self._text("EI_LOG_LEVEL", "INFO").upper()
        if level not in _LEVELS:
            raise ValueError(f"EI_LOG_LEVEL must be one of {', '.join(sorted(_LEVELS))}")
        return AppSettings(
            database_url=self._secrets.require("EI_DATABASE_URL"),
            rabbitmq_url=self._secrets.require("EI_RABBITMQ_URL"),
            queue_name=self._text("EI_QUEUE_NAME", "engineering-influence.jobs"),
            log_level=level,
            host=self._text("EI_HOST", "127.0.0.1"),
            port=self._port(),
            rate_burst=self._positive("EI_RATE_BURST", 30.0),
            rate_per_second=self._positive("EI_RATE_PER_SECOND", 10.0),
        )

    def _text(self, name: str, default: str) -> str:
        return self._environ.get(name, default).strip() or default

    def _port(self) -> int:
        raw = self._text("EI_PORT", "8000")
        if not raw.isdigit() or not 1 <= int(raw) <= 65535:
            raise ValueError("EI_PORT must be a port number from 1 to 65535")
        return int(raw)

    def _positive(self, name: str, default: float) -> float:
        raw = self._text(name, str(default))
        try:
            value = float(raw)
        except ValueError:
            raise ValueError(f"{name} must be a number") from None
        if value <= 0:
            raise ValueError(f"{name} must be positive")
        return value
