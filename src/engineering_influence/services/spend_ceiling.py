# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Holds the stack to the operator's spend ceilings."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager

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
    would wake it. The checks are made before anything is saved or queued, so a refusal leaves no trace.

    **A check and the save that follows it are one step.** ``hold()`` is a lock shared by every ceiling in the process;
    ``CreateRun`` and ``ResolveSpendConsent`` hold it from the check to the save, so many requests at once to one API or MCP
    process cannot each pass against the same total. Two *processes* (the API and a command line, say) each hold their own
    lock, so across processes the ceiling is a check with a window of a few milliseconds, not a lock; the per-run ceiling
    is exact either way.
    """

    _LOCK = threading.RLock()

    def __init__(self, runs: RunRepositoryInterface, limits: SpendLimits) -> None:
        """Remember the run repository and the spend limits the ceiling is checked against."""
        self._runs = runs
        self._limits = limits

    def admit_new(self, cap: int) -> None:
        """A new run whose cap is ``cap``."""
        self._admit(cap, cap)

    def admit_raise(self, run: BookRun, extra: int) -> None:
        """Raising ``run``'s cap by ``extra``."""
        self._admit(run.budget.cap + extra, extra)

    @contextmanager
    def hold(self) -> Iterator[None]:
        """The process-wide lock that makes a check and the save that follows it one step."""
        with self._LOCK:
            yield

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
