# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where artwork texture should recede so text stays legible."""

from typing import Any

import numpy as np
from numpy.typing import NDArray

from engineering_influence.infrastructure.covers.interfaces.quiet_zone_interface import (
    QuietZoneInterface,
)
from engineering_influence.infrastructure.covers.soft_rect import SoftRect
from engineering_influence.models.covers.cover_layout import CoverLayout


class QuietZone(QuietZoneInterface):
    """A soft mask over the back-cover text column and the spine."""

    def mask(self, layout: CoverLayout, h: int, w: int) -> NDArray[Any]:
        """The mask for a layout and image size."""
        m = np.zeros((h, w), np.float32)
        feather = layout.ppi * 0.35
        soft = SoftRect()
        if layout.back_safe is not None:
            m = np.maximum(
                m, soft.mask(h, w, layout.box_px(layout.back_safe.inset(-0.15)), feather)
            )
        if layout.spine is not None:
            m = np.maximum(
                m,
                soft.mask(h, w, layout.box_px(layout.spine.inset(-0.05, 0)), layout.ppi * 0.12),
            )
        return m
