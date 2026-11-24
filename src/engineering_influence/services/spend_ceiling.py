# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Holds the stack to the operator's spend ceilings."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.models.book_run import FINISHED, BookRun
from engineering_influence.models.spend_limits import SpendLimits
from engineering_influence.services.interfaces.spend_ceiling_interface import (
    SpendCeilingInterface,
)


class SpendCeiling(SpendCeilingInterface):
    """The same check for every way a cap can grow: a new run, and a grant to a run that asked for more.

    A run's **outstanding** budget is its cap less what it has spent, and only runs that have not finished count: a
    finished run can spend nothing more. A run that is parked or waiting for consent still counts, because a grant
    would wake it. The checks are made before anything is saved or queued, so a refusal leaves no trace. Two clients
    racing can each pass the check against the same total; the per-run ceiling is exact, and the outstanding ceiling
    is the limit a person sets with that much slack, not a lock.
    """

    def __init__(self, runs: RunRepositoryInterface, limits: SpendLimits) -> None:
        self._runs = runs
        self._limits = limits

    def admit_new(self, cap: int) -> None:
        """A new run whose cap is ``cap``."""
        self._admit(cap, cap)

    def admit_raise(self, run: BookRun, extra: int) -> None:
        """Raising ``run``'s cap by ``extra``."""
        self._admit(run.budget.cap + extra, extra)

    def outstanding(self) -> int:
        """The unspent budget of every unfinished run, in micro-dollars."""
        total = 0
        for run_id in self._runs.run_ids():
            run = self._runs.get(run_id)
            if run is not None and run.status not in FINISHED:
                total += run.budget.cap - run.budget.spent
        return total

    def _admit(self, new_cap: int, added: int) -> None:
        per_run = self._limits.per_run
        if per_run is not None and new_cap > per_run:
            raise ApplicationError(
                code="BUDGET_ABOVE_LIMIT",
                message=f"a run may be given at most {per_run} micro-USD in all; this would make its cap {new_cap}",
                http_status=422,
            )
        limit = self._limits.outstanding
        if limit is not None:
            held = self.outstanding()
            if held + added > limit:
                raise ApplicationError(
                    code="OUTSTANDING_BUDGET_EXCEEDED",
                    message=f"all runs together may hold at most {limit} micro-USD of unspent budget; "
                    f"they hold {held} and this adds {added}",
                    http_status=422,
                )
