# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of a run's budget, in whole micro-dollars."""

from pydantic import BaseModel, ConfigDict

from engineering_influence.contracts.run.v1.interfaces.run_budget_v1_interface import (
    RunBudgetV1Interface,
)


class RunBudgetV1(RunBudgetV1Interface, BaseModel):
    """The cap, what has been spent, what in-flight calls hold, and what is left."""

    model_config = ConfigDict(frozen=True)

    cap_micro_usd: int
    spent_micro_usd: int
    reserved_micro_usd: int
    remaining_micro_usd: int
