# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TextPlacementCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

    from engineering_influence.models.covers.cover_layout import CoverLayout


class TextPlacementCheckInterface(ABC):
    """Checks the transparent text layer against the layout."""

    __slots__ = ()

    @abstractmethod
    def run(self, layer: Image.Image, L: CoverLayout) -> list[str]:
        """Return a problem for stray text and for text over the barcode."""
