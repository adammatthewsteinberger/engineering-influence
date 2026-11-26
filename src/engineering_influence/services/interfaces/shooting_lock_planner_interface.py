# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ShootingLockPlanner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.shooting_lock import ShootingLock


class ShootingLockPlannerInterface(ABC):
    """Works out the numbers of a shooting script from the lock it already has."""

    __slots__ = ()

    @abstractmethod
    def plan(self, previous: ShootingLock, cards: tuple[int, ...]) -> ShootingLock:
        """The lock for the script's scene cards, given in script order: each locked scene keeps its number, each new
        scene is numbered after the scene before it, and each locked scene the script no longer has is omitted in
        place. Raises ValueError when a locked scene has moved or no number is free."""
