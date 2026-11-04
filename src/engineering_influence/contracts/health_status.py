# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Result of one dependency check."""

from pydantic import BaseModel, ConfigDict


class HealthStatus(BaseModel):
    """Whether one dependency is usable, with a short reason when it is not."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    healthy: bool
    detail: str | None = None
