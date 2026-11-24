# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BudgetPlanner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_brief import BookBrief
    from engineering_influence.models.budget_plan import BudgetPlan


class BudgetPlannerInterface(ABC):
    """Sets a brief's cap against what its book is expected to cost."""

    __slots__ = ()

    @abstractmethod
    def plan(self, brief: BookBrief) -> BudgetPlan:
        """The plan for the brief: its cap, the estimate and the grade."""
