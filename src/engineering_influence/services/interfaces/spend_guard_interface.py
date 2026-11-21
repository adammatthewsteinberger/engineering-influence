# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SpendGuard."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.budget import Budget


class SpendGuardInterface(ABC):
    """The one place in a process that decides whether a call may be made against a run's cap."""

    __slots__ = ()

    @abstractmethod
    def budget(self) -> Budget:
        """The budget as it stands, reservations included."""

    @abstractmethod
    def reserve(self, amount: int) -> None:
        """Hold ``amount`` for one call, or raise BudgetExceededError and hold nothing."""

    @abstractmethod
    def settle(self, reserved: int, actual: int) -> None:
        """Release a reservation and book what the call really cost."""

    @abstractmethod
    def release(self, reserved: int) -> None:
        """Release a reservation for a call that made no charge."""
