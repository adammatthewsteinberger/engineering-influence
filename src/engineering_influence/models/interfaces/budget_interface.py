# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Budget."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.budget import Budget


class BudgetInterface(ABC):
    """A spend cap in integer micro-dollars, enforced by reserving before every call."""

    __slots__ = ()

    @abstractmethod
    def remaining(self) -> int:
        """Micro-dollars still free to reserve."""

    @abstractmethod
    def reserve(self, amount: int) -> Budget:
        """Hold ``amount`` for one call; refuse when it does not fit under the cap."""

    @abstractmethod
    def settle(self, reserved: int, actual: int) -> Budget:
        """Release a reservation and book what the call really cost (zero if it failed)."""
