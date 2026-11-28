# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a book is expected to cost before any of it is written."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.cost_estimate_interface import CostEstimateInterface


@dataclass(frozen=True, slots=True)
class CostEstimate(CostEstimateInterface):
    """The expected micro-dollars of each stage, and whether the book can be finished without it.

    A stage is **essential** when the book cannot be finished without its output (the planning stages and the draft)
    and **optional** when the book can (the editing passes: a run that has no money left for one keeps the text it
    had). The figures are estimates from the brief alone, before the outline says how many chapters there are, so
    they are expected values with a margin, not bounds: ``high`` is the expected figure plus ``MARGIN_PERCENT``.
    """

    MARGIN_PERCENT: ClassVar[int] = 50

    stages: tuple[tuple[str, int, bool], ...]

    def __post_init__(self) -> None:
        """Validate the estimated costs when the estimate is built."""
        if not isinstance(self.stages, tuple) or not self.stages:
            raise ValueError("an estimate has at least one stage")
        names = [name for name, _, _ in self.stages]
        if len(set(names)) != len(names):
            raise ValueError("an estimate names each stage once")
        if any(type(cost) is not int or cost < 0 for _, cost, _ in self.stages):
            raise ValueError("a stage costs a whole number of micro-dollars, not less than none")

    def expected(self) -> int:
        """Every stage, as expected."""
        return sum(cost for _, cost, _ in self.stages)

    def essential(self) -> int:
        """The stages without which the book cannot be finished, as expected."""
        return sum(cost for _, cost, essential in self.stages if essential)

    def optional(self) -> int:
        """The editing, as expected."""
        return self.expected() - self.essential()

    def high(self, micro_usd: int) -> int:
        """``micro_usd`` with the margin added, rounded up."""
        return -(-micro_usd * (100 + self.MARGIN_PERCENT) // 100)
