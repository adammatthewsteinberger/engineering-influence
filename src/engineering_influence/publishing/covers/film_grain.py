"""Uniform film grain."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


class FilmGrain:
    """Adds zero-mean noise to an image in place."""

    def add(self, img: NDArray[Any], rng: np.random.Generator, amount: float) -> None:
        """Add grain of the given amplitude."""
        img += (rng.random(img.shape[:2], dtype=np.float32)[..., None] - 0.5) * amount
