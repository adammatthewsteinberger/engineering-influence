# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of the body that grants a run more budget."""

from pydantic import BaseModel, ConfigDict, Field

from engineering_influence.contracts.run.v1.interfaces.run_grant_v1_interface import (
    RunGrantV1Interface,
)


class RunGrantV1(RunGrantV1Interface, BaseModel):
    """Omit `micro_usd` to grant the amount a run waiting for consent asked for.

    A parked run has no request, so it needs an amount to continue with.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    micro_usd: int | None = Field(default=None, gt=0)
