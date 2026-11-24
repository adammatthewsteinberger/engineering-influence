# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether a run's cap is enough for the book it asks for."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.cost_estimate import CostEstimate
from engineering_influence.models.interfaces.budget_plan_interface import BudgetPlanInterface


@dataclass(frozen=True, slots=True)
class BudgetPlan(BudgetPlanInterface):
    """A cap set against an estimate, in four grades.

    ``short``: the cap is below what the essential stages are expected to cost, so the book probably cannot be finished.
    ``tight``: it covers them as expected but not with the margin, so the run may stop to ask for more. ``lean``: it
    covers them with the margin but not the whole book with the margin, so an editing pass may be skipped if the money runs
    out (a run keeps the text it had; nothing stops). ``ample``: it covers every stage with the margin.
    """

    SHORT: ClassVar[str] = "short"
    TIGHT: ClassVar[str] = "tight"
    LEAN: ClassVar[str] = "lean"
    AMPLE: ClassVar[str] = "ample"

    cap: int
    estimate: CostEstimate

    def __post_init__(self) -> None:
        if type(self.cap) is not int or self.cap < 1:
            raise ValueError("a cap is a whole number of micro-dollars above zero")

    def grade(self) -> str:
        """How the cap measures up: short, tight, lean or ample."""
        essential = self.estimate.essential()
        if self.cap < essential:
            return self.SHORT
        if self.cap < self.estimate.high(essential):
            return self.TIGHT
        if self.cap < self.estimate.high(self.estimate.expected()):
            return self.LEAN
        return self.AMPLE

    def suggested(self) -> int:
        """A cap that covers every stage, editing included, with the estimate's margin."""
        return self.estimate.high(self.estimate.expected())
