# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One run that turns a brief into a book, as an immutable value."""

from dataclasses import dataclass, replace

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.budget import Budget
from engineering_influence.models.interfaces.book_run_interface import BookRunInterface
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.models.stage_plan import StagePlan

FINISHED = frozenset({RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED})


@dataclass(frozen=True, slots=True)
class BookRun(BookRunInterface):
    """The brief, the plan, the money and where the run stands.

    Every change returns a new run, so a repository can store each step and a resumed run
    picks up exactly where the last stored one stopped. ``stage`` defaults to the plan's first.
    """

    run_id: str
    brief: BookBrief
    plan: StagePlan
    budget: Budget
    stage: str = ""
    status: RunStatus = RunStatus.PENDING
    issues: tuple[QualityIssue, ...] = ()
    # Set while the run waits for the person to grant more budget; None otherwise.
    consent: SpendRequest | None = None
    # The locked MCP servers this run may use: None for every granted server (the default for
    # runs made by the command line), or the names a session selected, possibly none.
    servers: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("a run needs an id")
        if self.plan.kind is not self.brief.kind:
            raise ValueError("the plan is for a different kind of book")
        if self.servers is not None and len(set(self.servers)) != len(self.servers):
            raise ValueError("a run names each of its servers once")
        if not self.stage:
            object.__setattr__(self, "stage", self.plan.first())
        elif self.stage not in self.plan.stages:
            raise ValueError(f"{self.stage!r} is not a stage of this plan")

    def start(self) -> "BookRun":
        """Mark a pending run as running, before its first stage begins."""
        if self.status is not RunStatus.PENDING:
            raise ValueError("only a pending run can start")
        return replace(self, status=RunStatus.RUNNING)

    def advance(self) -> "BookRun":
        """Move to the next stage, or complete the run after the last one."""
        self._require_unfinished()
        following = self.plan.after(self.stage)
        if following is None:
            return replace(self, status=RunStatus.COMPLETED)
        return replace(self, stage=following, status=RunStatus.RUNNING)

    def park(self) -> "BookRun":
        """Stop for lack of credit; ``resume`` continues from the same stage."""
        self._require_unfinished()
        return replace(self, status=RunStatus.PARKED_CAPACITY)

    def resume(self) -> "BookRun":
        """Continue a parked run."""
        if self.status is not RunStatus.PARKED_CAPACITY:
            raise ValueError("only a parked run can resume")
        return replace(self, status=RunStatus.RUNNING)

    def fail(self) -> "BookRun":
        """End the run as failed."""
        self._require_unfinished()
        return replace(self, status=RunStatus.FAILED)

    def cancel(self) -> "BookRun":
        """End the run because someone asked it to stop."""
        self._require_unfinished()
        return replace(self, status=RunStatus.CANCELLED)

    def await_consent(self, request: SpendRequest) -> "BookRun":
        """Stop until the person grants the request or denies it."""
        self._require_unfinished()
        return replace(self, status=RunStatus.AWAITING_CONSENT, consent=request)

    def grant(self, micro_usd: int | None = None) -> "BookRun":
        """Raise the cap and continue.

        A run waiting for consent gets exactly the amount it asked for; passing a different amount
        is refused. A parked run needs an amount, and gets exactly that.
        """
        if self.status is RunStatus.AWAITING_CONSENT and self.consent is not None:
            requested = self.consent.requested_micro_usd
            if micro_usd is not None and micro_usd != requested:
                raise ValueError("a consent grant is for exactly the amount the run asked for")
            extra = requested
        elif self.status is RunStatus.PARKED_CAPACITY:
            if micro_usd is None or micro_usd <= 0:
                raise ValueError("a parked run needs a positive amount to continue with")
            extra = micro_usd
        else:
            raise ValueError("only a run waiting for consent or parked can be granted more budget")
        budget = Budget(cap=self.budget.cap + extra, spent=self.budget.spent)
        return replace(self, budget=budget, status=RunStatus.RUNNING, consent=None)

    def deny(self) -> "BookRun":
        """Refuse the request: the run parks, and stays parked until it is granted more budget."""
        if self.status is not RunStatus.AWAITING_CONSENT:
            raise ValueError("only a run waiting for consent can be denied")
        return replace(self, status=RunStatus.PARKED_CAPACITY, consent=None)

    def with_budget(self, budget: Budget) -> "BookRun":
        """The run with its budget replaced, after a reservation or a settlement."""
        return replace(self, budget=budget)

    def with_issue(self, issue: QualityIssue) -> "BookRun":
        """The run with one more recorded issue."""
        return replace(self, issues=(*self.issues, issue))

    def has_blocking_issue(self) -> bool:
        """True when any recorded issue should stop a release."""
        return any(issue.blocking for issue in self.issues)

    def _require_unfinished(self) -> None:
        if self.status in FINISHED:
            raise ValueError("the run is already finished")
