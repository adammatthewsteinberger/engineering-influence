# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Feathered rectangular masks."""

from typing import Any

import numpy as np
from numpy.typing import NDArray

from engineering_influence.publishing.covers.box_blur import BoxBlur


class SoftRect:
    """A rectangle of ones, blurred at the edges."""

    def mask(self, h: int, w: int, box: tuple[int, int, int, int], feather: float) -> NDArray[Any]:
        """The feathered mask for a pixel box."""
        m = np.zeros((h, w), np.float32)
        x0, y0, x1, y1 = box
        m[max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)] = 1.0
        return BoxBlur().apply(m, feather)
