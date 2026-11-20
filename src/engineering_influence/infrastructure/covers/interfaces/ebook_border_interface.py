# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EbookBorder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


class EbookBorderInterface(ABC):
    """Detects a light edge and frames the cover in medium gray."""

    __slots__ = ()

    @abstractmethod
    def is_light_edge(self, img: Image.Image, inset: int = 4, band: int = 24) -> bool:
        """True when the outer band of the picture is near white (Rec. 709 luminance > 0.8)."""

    @abstractmethod
    def add(self, img: Image.Image) -> Image.Image:
        """A copy of the image with the border drawn on."""
