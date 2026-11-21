# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reserve before every model call, so concurrent calls can never spend past the cap."""

import threading

from engineering_influence.errors.budget_exceeded_error import BudgetExceededError
from engineering_influence.models.budget import Budget
from engineering_influence.services.interfaces.spend_guard_interface import SpendGuardInterface


class SpendGuard(SpendGuardInterface):
    """A run's budget behind a lock, shared by every call that stage makes in this process.

    Start it from ``Budget(cap, spent=<what the journal already holds>)``. A reservation lives
    inside one call, so nothing here is saved: ``AdvanceRun`` rebuilds ``spent`` from the journal.
    If a call cost more than it reserved, the amount reserved is booked, the reservation is
    released, and BudgetExceededError is raised, because the budget cannot represent overspend.
    The journal holds the true figure, and ``AdvanceRun`` fails the run if it passes the cap.
    """

    def __init__(self, budget: Budget) -> None:
        self._budget = budget
        self._lock = threading.Lock()

    def budget(self) -> Budget:
        """The budget as it stands, reservations included."""
        with self._lock:
            return self._budget

    def reserve(self, amount: int) -> None:
        """Hold ``amount`` for one call, or raise BudgetExceededError and hold nothing."""
        with self._lock:
            self._budget = self._budget.reserve(amount)

    def settle(self, reserved: int, actual: int) -> None:
        """Release a reservation and book what the call really cost."""
        with self._lock:
            try:
                self._budget = self._budget.settle(reserved, actual)
            except BudgetExceededError:
                self._budget = self._budget.settle(reserved, reserved)
                raise

    def release(self, reserved: int) -> None:
        """Release a reservation for a call that made no charge."""
        self.settle(reserved, 0)
