# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FontLoader."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import ImageFont


class FontLoaderInterface(ABC):
    """The first directory that holds the file wins."""

    __slots__ = ()

    @abstractmethod
    def load(self, name: str, size_px: float) -> ImageFont.FreeTypeFont:
        """Load a font at a pixel size (rounded up, minimum 6)."""
