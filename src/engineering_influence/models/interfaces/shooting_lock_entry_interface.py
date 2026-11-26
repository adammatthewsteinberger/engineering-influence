# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ShootingLockEntry."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ShootingLockEntryInterface(ABC):
    """One scene's place in the locked shooting script."""

    __slots__ = ()

    @abstractmethod
    def sort_key(self) -> tuple[int, str]:
        """The number and the letter of the scene's label: the order the labels run in, so 42 comes before 42A and 43."""
