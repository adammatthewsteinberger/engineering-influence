# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PageFileNumber."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PageFileNumberInterface(ABC):
    """Natural ordering for names such as render-0012.png."""

    __slots__ = ()

    @abstractmethod
    def of(self, path: Path) -> int:
        """The trailing number of a .png file name, or 0 when there is none."""
