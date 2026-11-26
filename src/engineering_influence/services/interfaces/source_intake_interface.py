# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SourceIntake."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.source_entry import SourceEntry


class SourceIntakeInterface(ABC):
    """Turns an author's folder of source files into numbered, digest-pinned entries for a run."""

    __slots__ = ()

    @abstractmethod
    def intake(self, folder: Path) -> tuple[SourceEntry, ...]:
        """The folder's sources, numbered from 1 in file-name order, each with its digest."""
