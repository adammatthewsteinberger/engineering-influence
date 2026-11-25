# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Box."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.covers.box import Box


class BoxInterface(ABC):
    """Left, top, right, bottom edges."""

    __slots__ = ()

    @property
    @abstractmethod
    def w(self) -> float:
        """Width."""

    @property
    @abstractmethod
    def h(self) -> float:
        """Height."""

    @abstractmethod
    def inset(
        self,
        left: float,
        top: float | None = None,
        right: float | None = None,
        bottom: float | None = None,
    ) -> Box:
        """Shrink by the given amounts; omitted sides repeat the previous one."""
