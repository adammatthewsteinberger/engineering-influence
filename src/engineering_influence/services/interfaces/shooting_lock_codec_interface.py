# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ShootingLockCodec."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.shooting_lock import ShootingLock


class ShootingLockCodecInterface(ABC):
    """Writes a shooting script lock as text and reads it back."""

    __slots__ = ()

    @abstractmethod
    def encode(self, lock: ShootingLock) -> str:
        """The lock as text, so that decode gives back the same lock."""

    @abstractmethod
    def decode(self, text: str) -> ShootingLock:
        """The lock the text holds, or an ApplicationError when the text is not a lock this version reads."""
