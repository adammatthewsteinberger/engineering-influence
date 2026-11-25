# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A call that would spend more than the run's budget allows."""

from engineering_influence.errors.interfaces.budget_exceeded_error_interface import (
    BudgetExceededErrorInterface,
)


class BudgetExceededError(BudgetExceededErrorInterface, ValueError):
    """Raised when a reservation does not fit or a call cost more than it reserved.

    It is a ``ValueError`` so code that already catches budget problems that way keeps working.
    """
