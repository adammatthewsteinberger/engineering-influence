# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CoverLayout."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.covers.box import Box


class CoverLayoutInterface(ABC):
    """Everything in inches except ppi; kind is "ebook", "paperback", or "hardcover"."""

    __slots__ = ()

    @property
    @abstractmethod
    def px(self) -> tuple[int, int]:
        """Image size; rounds up so it is at least `ppi` across the exact KDP page size."""

    @abstractmethod
    def to_px(self, v: float) -> float:
        """Inches to pixels."""

    @abstractmethod
    def box_px(self, b: Box) -> tuple[int, int, int, int]:
        """A box in pixels."""
