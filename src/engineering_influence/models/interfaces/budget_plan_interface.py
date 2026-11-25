# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BudgetPlan."""

from abc import ABC, abstractmethod


class BudgetPlanInterface(ABC):
    """Whether a cap is enough for a book, and how much would be."""

    __slots__ = ()

    @abstractmethod
    def suggested(self) -> int:
        """A cap that covers every stage with the estimate's margin, in micro-dollars."""
