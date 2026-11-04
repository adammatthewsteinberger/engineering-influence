"""Colour and mask arithmetic for painters."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


class Compositing:
    """Smoothstep, mixing, colours, and in-place compositing through masks."""

    def smoothstep(self, e0: float, e1: float, x: NDArray[Any]) -> NDArray[Any]:
        """Hermite interpolation between two edges."""
        t = np.clip((x - e0) / (e1 - e0), 0, 1)
        return t * t * (3 - 2 * t)

    def mix(self, a: Any, b: Any, t: Any) -> Any:
        """Linear blend from a to b."""
        return a + (b - a) * t

    def rgb(self, *c: float) -> NDArray[Any]:
        """A float32 colour."""
        return np.array(c, np.float32)

    def over(self, img: NDArray[Any], mask: NDArray[Any], color: Any, alpha: float = 1.0) -> None:
        """Composite a flat colour through a coverage mask, in place."""
        m = (mask * alpha)[..., None]
        img *= 1 - m
        img += m * np.asarray(color, np.float32)

    def add_light(
        self, img: NDArray[Any], mask: NDArray[Any], color: Any, gain: float = 1.0
    ) -> None:
        """Additive light (glows), in place."""
        img += (mask * gain)[..., None] * np.asarray(color, np.float32)
