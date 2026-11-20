# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for LayoutCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.covers.cover_layout import CoverLayout


class LayoutCheckInterface(ABC):
    """Reports each rule a layout breaks."""

    __slots__ = ()

    @abstractmethod
    def run(self, layout: CoverLayout) -> list[str]:
        """Return layout problems; an empty list means the layout is within KDP's limits."""
