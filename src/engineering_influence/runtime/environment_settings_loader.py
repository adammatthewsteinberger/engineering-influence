# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Read process settings from the environment, failing closed on anything missing."""

import os
from collections.abc import Mapping

from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.spend_limits import SpendLimits
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.interfaces.environment_settings_loader_interface import (
    EnvironmentSettingsLoaderInterface,
)

_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class EnvironmentSettingsLoader(EnvironmentSettingsLoaderInterface):
    """``EI_DATABASE_URL`` and ``EI_RABBITMQ_URL`` are required; the rest have safe defaults.

    ``EI_MCP_ALLOW_SPEND`` (``1``, ``true`` or ``yes``) lets the MCP server grant and deny a run's budget requests; off by
    default, so an agent cannot spend more than a run's cap. ``EI_MCP_MAX_RUN_BUDGET_MICRO_USD`` (default 5,000,000, five
    dollars) is the most a run started over MCP may be given.

    The API binds to loopback unless ``EI_HOST`` says otherwise, so a bare run is never
    reachable from the network by accident.
    """

    def __init__(
        self, secrets: SecretProviderInterface, environ: Mapping[str, str] | None = None
    ) -> None:
        self._secrets = secrets
        self._environ = os.environ if environ is None else environ

    def load(self) -> AppSettings:
        """Return validated settings or raise with the name of the offending variable."""
        level = self._text("EI_LOG_LEVEL", "INFO").upper()
        if level not in _LEVELS:
            raise ValueError(f"EI_LOG_LEVEL must be one of {', '.join(sorted(_LEVELS))}")
        webhook_urls = self._urls()
        return AppSettings(
            database_url=self._secrets.require("EI_DATABASE_URL"),
            rabbitmq_url=self._secrets.require("EI_RABBITMQ_URL"),
            queue_name=self._text("EI_QUEUE_NAME", "engineering-influence.jobs"),
            log_level=level,
            host=self._text("EI_HOST", "127.0.0.1"),
            port=self._port(),
            rate_burst=self._positive("EI_RATE_BURST", 30.0),
            rate_per_second=self._positive("EI_RATE_PER_SECOND", 10.0),
            mcp_allow_spend=self._text("EI_MCP_ALLOW_SPEND", "").lower() in ("1", "true", "yes"),
            mcp_max_run_budget_micro_usd=self._whole("EI_MCP_MAX_RUN_BUDGET_MICRO_USD", 5_000_000),
            spend_limits=SpendLimits.from_environment(self._environ),
            webhook_urls=webhook_urls,
            webhook_secret=self._secrets.require("EI_WEBHOOK_SECRET") if webhook_urls else "",
            webhook_interval_seconds=self._positive("EI_WEBHOOK_INTERVAL_SECONDS", 5.0),
        )

    def _urls(self) -> tuple[str, ...]:
        """The webhook receivers: a comma-separated list of https:// addresses, empty when none is configured."""
        urls = tuple(
            part.strip() for part in self._text("EI_WEBHOOK_URLS", "").split(",") if part.strip()
        )
        if any(not url.startswith("https://") for url in urls):
            raise ValueError("EI_WEBHOOK_URLS must hold https:// addresses only")
        return urls

    def _text(self, name: str, default: str) -> str:
        return self._environ.get(name, default).strip() or default

    def _port(self) -> int:
        raw = self._text("EI_PORT", "8000")
        if not raw.isdigit() or not 1 <= int(raw) <= 65535:
            raise ValueError("EI_PORT must be a port number from 1 to 65535")
        return int(raw)

    def _whole(self, name: str, default: int) -> int:
        raw = self._text(name, str(default))
        if not raw.isdigit() or int(raw) < 1:
            raise ValueError(f"{name} must be a whole number above zero")
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
