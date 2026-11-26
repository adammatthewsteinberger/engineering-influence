# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ShootingLock."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ShootingLockInterface(ABC):
    """The locked scenes of a shooting script."""

    __slots__ = ()

    @abstractmethod
    def numbered_cards(self) -> tuple[int, ...]:
        """Every locked scene card, in script order, omitted scenes included."""
