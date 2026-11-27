# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BibleIntake."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.bible_card import BibleCard


class BibleIntakeInterface(ABC):
    """Reads a whole bible folder and checks it before any run uses it."""

    __slots__ = ()

    @abstractmethod
    def intake(self, folder: Path) -> tuple[BibleCard, ...]:
        """Every card in the folder, sorted by kind and id, once the whole bible has passed its checks."""
