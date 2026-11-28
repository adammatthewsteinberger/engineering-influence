# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Validated process settings."""

from dataclasses import dataclass, field

from engineering_influence.models.spend_limits import SpendLimits
from engineering_influence.runtime.interfaces.app_settings_interface import AppSettingsInterface


@dataclass(frozen=True, slots=True)
class AppSettings(AppSettingsInterface):
    """Everything a process needs from its environment.

    ``database_url`` and ``rabbitmq_url`` carry credentials, so they are never logged. ``spend_limits`` are the operator's
    ceilings on what any run, and all runs together, may be allowed to spend; none is set by default.
    """

    database_url: str
    rabbitmq_url: str
    queue_name: str = "engineering-influence.jobs"
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    rate_burst: float = 30.0
    rate_per_second: float = 10.0
    mcp_allow_spend: bool = False
    mcp_max_run_budget_micro_usd: int = 5_000_000
    spend_limits: SpendLimits = field(default_factory=SpendLimits)
    webhook_urls: tuple[str, ...] = ()
    webhook_secret: str = ""
    webhook_interval_seconds: float = 5.0
    artifact_store: str = "database"
    otlp_endpoint: str = ""
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = "us-east-1"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""

    def __repr__(self) -> str:
        """Show the settings without the secrets: the queue name, log level, host and port only."""
        return (
            f"AppSettings(queue_name={self.queue_name!r}, log_level={self.log_level!r}, "
            f"host={self.host!r}, port={self.port})"
        )
