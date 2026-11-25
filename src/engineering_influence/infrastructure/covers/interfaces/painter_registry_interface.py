# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PainterRegistry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.cover_painter_interface import CoverPainterInterface


class PainterRegistryInterface(ABC):
    """Maps the painter name in a style to the painter that draws it."""

    __slots__ = ()

    @abstractmethod
    def register(self, name: str, painter: CoverPainterInterface) -> None:
        """Add a painter; a later registration under the same name replaces the earlier one."""

    @abstractmethod
    def get(self, name: str) -> CoverPainterInterface:
        """Return the painter, or fail with the names that are available."""
