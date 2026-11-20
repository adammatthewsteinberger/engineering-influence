# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for LayoutFactory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.covers.cover_layout import CoverLayout


class LayoutFactoryInterface(ABC):
    """Spine width follows page count; the back cover keeps a clear barcode box."""

    __slots__ = ()

    @abstractmethod
    def ebook(self) -> CoverLayout:
        """The 1600 x 2560 px Kindle cover."""

    @abstractmethod
    def paperback(self, pages: int) -> CoverLayout:
        """Back + spine + front with bleed."""

    @abstractmethod
    def hardcover(self, pages: int) -> CoverLayout:
        """Case laminate: boards, hinge, spine, and a 15 mm wrap."""
