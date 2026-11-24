# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Plans a run's money before it spends any."""

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.budget_plan import BudgetPlan
from engineering_influence.services.interfaces.budget_planner_interface import (
    BudgetPlannerInterface,
)
from engineering_influence.services.interfaces.cost_estimator_interface import (
    CostEstimatorInterface,
)


class BudgetPlanner(BudgetPlannerInterface):
    """A cap that cannot finish the book is found out before the first call, not after most of it is paid for.

    The planner only grades: it does not change the cap or refuse a run. Who acts on a ``short`` plan is the caller's
    choice (``ei book create`` refuses it).
    """

    def __init__(self, estimator: CostEstimatorInterface) -> None:
        self._estimator = estimator

    def plan(self, brief: BookBrief) -> BudgetPlan:
        """The plan for the brief: its cap, the estimate and the grade."""
        return BudgetPlan(brief.budget_micro_usd, self._estimator.estimate(brief))
