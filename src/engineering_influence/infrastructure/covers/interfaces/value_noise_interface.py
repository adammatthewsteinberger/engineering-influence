# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ValueNoise."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    import numpy as np
    from numpy.typing import NDArray


class ValueNoiseInterface(ABC):
    """Single-octave noise and fractal (fBm) sums of it, both in [0, 1]."""

    __slots__ = ()

    @abstractmethod
    def noise(self, h: int, w: int, cells: float, rng: np.random.Generator) -> NDArray[Any]:
        """Smooth value noise with about `cells` features across the width."""

    @abstractmethod
    def fbm(
        self,
        h: int,
        w: int,
        cells: float,
        octaves: int,
        rng: np.random.Generator,
        gain: float = 0.5,
    ) -> NDArray[Any]:
        """Octaves of noise, each twice as fine, normalised back into [0, 1]."""
