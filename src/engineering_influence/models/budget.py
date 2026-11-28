# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A spend cap in integer micro-dollars, enforced by reserving before every call."""

from dataclasses import dataclass

from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.models.interfaces.budget_interface import BudgetInterface


@dataclass(frozen=True, slots=True)
class Budget(BudgetInterface):
    """What a run may spend, what it has spent, and what in-flight calls have reserved.

    Amounts are whole micro-dollars (1,000,000 = one dollar), never floats, so the sums are
    exact. A call reserves its worst-case cost first; the reservation is what keeps
    ``spent + reserved`` at or under ``cap`` however many calls are in flight.
    """

    cap: int
    spent: int = 0
    reserved: int = 0

    def __post_init__(self) -> None:
        """Validate the budget's cap, spending and reservations when it is built."""
        if min(self.cap, self.spent, self.reserved) < 0:
            raise ValueError("budget amounts cannot be negative")
        if self.spent + self.reserved > self.cap:
            raise BudgetExceededError("spent and reserved cannot exceed the cap")

    def remaining(self) -> int:
        """Micro-dollars still free to reserve."""
        return self.cap - self.spent - self.reserved

    def reserve(self, amount: int) -> "Budget":
        """Hold ``amount`` for one call; refuse when it does not fit under the cap."""
        if amount < 0:
            raise ValueError("a reservation cannot be negative")
        if amount > self.remaining():
            raise BudgetExceededError("reservation exceeds the remaining budget")
        return Budget(cap=self.cap, spent=self.spent, reserved=self.reserved + amount)

    def settle(self, reserved: int, actual: int) -> "Budget":
        """Release a reservation and book what the call really cost (zero if it failed)."""
        if reserved < 0 or actual < 0:
            raise ValueError("settled amounts cannot be negative")
        if reserved > self.reserved:
            raise ValueError("cannot settle more than is reserved")
        if actual > reserved:
            raise BudgetExceededError("actual cost exceeds the reservation")
        return Budget(cap=self.cap, spent=self.spent + actual, reserved=self.reserved - reserved)
