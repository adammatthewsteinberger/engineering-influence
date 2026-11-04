# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Result of checking every dependency."""

from pydantic import BaseModel, ConfigDict

from engineering_influence.contracts.health_status import HealthStatus


class ReadinessReport(BaseModel):
    """Ready only when every dependency check is healthy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ready: bool
    checks: tuple[HealthStatus, ...]
