"""The interface a cover painter implements."""

from abc import ABC, abstractmethod
from typing import Any

from numpy.typing import NDArray

from engineering_influence.publishing.covers.cover_layout import CoverLayout
from engineering_influence.publishing.covers.cover_style import CoverStyle


class CoverPainter(ABC):
    """Paints the full cover image, text excluded, as float RGB in [0, 1].

    Painters must be deterministic for a given layout and style (seed from style.seed), so a
    rebuild of unchanged sources produces identical files.
    """

    @abstractmethod
    def paint(self, layout: CoverLayout, style: CoverStyle) -> NDArray[Any]:
        """Return an (height, width, 3) float array for layout.px."""
