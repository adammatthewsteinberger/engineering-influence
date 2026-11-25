# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for InteriorPageCount."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class InteriorPageCountInterface(ABC):
    """Reads the finished interior, never an estimate."""

    __slots__ = ()

    @abstractmethod
    def of(self, pdf: Path) -> int:
        """The number of pages, or an error telling you to build the interior first."""
