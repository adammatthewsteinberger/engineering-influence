# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of one issue a run recorded."""

from pydantic import BaseModel, ConfigDict

from engineering_influence.contracts.run.v1.interfaces.run_issue_v1_interface import (
    RunIssueV1Interface,
)


class RunIssueV1(RunIssueV1Interface, BaseModel):
    """Where it happened, a stable code, a short detail, and whether it stops a release."""

    model_config = ConfigDict(frozen=True)

    stage: str
    code: str
    detail: str
    blocking: bool
