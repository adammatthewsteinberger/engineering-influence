# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Uniform film grain."""

from typing import Any

import numpy as np
from numpy.typing import NDArray

from engineering_influence.infrastructure.covers.interfaces.film_grain_interface import (
    FilmGrainInterface,
)


class FilmGrain(FilmGrainInterface):
    """Adds zero-mean noise to an image in place."""

    def add(self, img: NDArray[Any], rng: np.random.Generator, amount: float) -> None:
        """Add grain of the given amplitude."""
        img += (rng.random(img.shape[:2], dtype=np.float32)[..., None] - 0.5) * amount
