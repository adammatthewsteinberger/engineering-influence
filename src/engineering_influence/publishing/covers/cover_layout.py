"""The geometry of one cover image: panels, safe areas, spine, and barcode."""

import math
from dataclasses import dataclass

from engineering_influence.publishing.covers.box import Box


@dataclass
class CoverLayout:
    """Everything in inches except ppi; kind is "ebook", "paperback", or "hardcover"."""

    kind: str
    width: float
    height: float
    ppi: float
    front: Box  # visible front panel (trim or board)
    front_safe: Box  # where front text may go
    back: Box | None = None
    back_safe: Box | None = None
    spine: Box | None = None
    spine_safe: Box | None = None
    barcode: Box | None = None

    @property
    def px(self) -> tuple[int, int]:
        """Image size; rounds up so it is at least `ppi` across the exact KDP page size."""
        return (
            math.ceil(self.width * self.ppi - 1e-6),
            math.ceil(self.height * self.ppi - 1e-6),
        )

    def to_px(self, v: float) -> float:
        """Inches to pixels."""
        return v * self.ppi

    def box_px(self, b: Box) -> tuple[int, int, int, int]:
        """A box in pixels."""
        return (
            round(b.x0 * self.ppi),
            round(b.y0 * self.ppi),
            round(b.x1 * self.ppi),
            round(b.y1 * self.ppi),
        )
