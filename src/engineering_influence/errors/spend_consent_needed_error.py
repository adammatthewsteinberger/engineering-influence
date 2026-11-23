# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A model call needs more budget than the run's cap leaves; the run waits instead of failing."""

from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.errors.interfaces.spend_consent_needed_error_interface import (
    SpendConsentNeededErrorInterface,
)


class SpendConsentNeededError(SpendConsentNeededErrorInterface, BudgetExceededError):
    """A reservation that does not fit, carrying how many micro-dollars the call needs above the cap.

    It is a BudgetExceededError, so code that handles overspend keeps working, and the advance
    service checks for this one first, to park the run for consent instead of failing it.
    """

    def __init__(self, requested_micro_usd: int) -> None:
        super().__init__(
            f"the next call needs {requested_micro_usd} micro-USD beyond the run's cap"
        )
        self.requested_micro_usd = requested_micro_usd
