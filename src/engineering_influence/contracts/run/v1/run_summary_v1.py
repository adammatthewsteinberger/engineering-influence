# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Version 1 of what the API and the CLI report about a book run."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from engineering_influence.contracts.run.v1.interfaces.run_summary_v1_interface import (
    RunSummaryV1Interface,
)
from engineering_influence.contracts.run.v1.run_budget_v1 import RunBudgetV1
from engineering_influence.contracts.run.v1.run_issue_v1 import RunIssueV1
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.run_status import RunStatus


class RunSummaryV1(RunSummaryV1Interface, BaseModel):
    """Status, position in the plan, money, issues and the names of the artifacts made so far.

    The brief's idea is left out on purpose: it can be long and the summary is for watching a run,
    not for reading the book. Artifact bytes come from their own route.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: Literal[1] = 1
    run_id: str
    kind: BookKind
    status: RunStatus
    stage: str
    stages: tuple[str, ...]
    budget: RunBudgetV1
    issues: tuple[RunIssueV1, ...]
    artifacts: tuple[str, ...]

    @classmethod
    def from_run(cls, run: BookRun, artifacts: list[str]) -> "RunSummaryV1":
        """Describe a run and the artifacts it has stored."""
        return cls(
            run_id=run.run_id,
            kind=run.brief.kind,
            status=run.status,
            stage=run.stage,
            stages=run.plan.stages,
            budget=RunBudgetV1(
                cap_micro_usd=run.budget.cap,
                spent_micro_usd=run.budget.spent,
                reserved_micro_usd=run.budget.reserved,
                remaining_micro_usd=run.budget.remaining(),
            ),
            issues=tuple(
                RunIssueV1(
                    stage=issue.stage,
                    code=issue.code,
                    detail=issue.detail,
                    blocking=issue.blocking,
                )
                for issue in run.issues
            ),
            artifacts=tuple(artifacts),
        )
