"""Supersampled anti-aliased line and shape drawing into a coverage mask."""

from typing import Any

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw


class Ink:
    """Draws at `scale` times the resolution, then reduces to a float mask in [0, 1]."""

    def __init__(self, w: int, h: int, scale: int = 3) -> None:
        self.scale = scale
        self.img = Image.new("L", (w * scale, h * scale), 0)
        self.draw = ImageDraw.Draw(self.img)

    def line(self, pts: Any, width_px: float, value: int = 255) -> None:
        """A curved-joint polyline."""
        s = self.scale
        self.draw.line(
            [(x * s, y * s) for x, y in pts],
            fill=value,
            width=max(1, round(width_px * s)),
            joint="curve",
        )

    def ellipse(
        self,
        cx: float,
        cy: float,
        rx: float,
        ry: float,
        value: int = 255,
        outline_px: float | None = None,
    ) -> None:
        """A filled or outlined ellipse."""
        s = self.scale
        box = [(cx - rx) * s, (cy - ry) * s, (cx + rx) * s, (cy + ry) * s]
        if outline_px is None:
            self.draw.ellipse(box, fill=value)
        else:
            self.draw.ellipse(box, outline=value, width=max(1, round(outline_px * s)))

    def polygon(self, pts: Any, value: int = 255) -> None:
        """A filled polygon."""
        s = self.scale
        self.draw.polygon([(x * s, y * s) for x, y in pts], fill=value)

    def mask(self) -> NDArray[Any]:
        """The accumulated coverage as float32 in [0, 1]."""
        small = self.img.reduce(self.scale)
        return np.asarray(small, dtype=np.float32) / 255.0
