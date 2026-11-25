# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CoverRenderer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from PIL import Image

    from engineering_influence.models.covers.cover_layout import CoverLayout
    from engineering_influence.models.covers.cover_style import CoverStyle


class CoverRendererInterface(ABC):
    """Painter output plus ordered dither, then front, back, and spine text on a layer."""

    __slots__ = ()

    @abstractmethod
    def render(self, L: CoverLayout, st: CoverStyle, meta: dict[str, Any]) -> Image.Image:
        """Return the finished RGB cover, or fail when the text or layout breaks a KDP rule."""
