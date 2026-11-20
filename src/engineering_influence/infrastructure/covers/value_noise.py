# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Smooth value noise for generative painters."""

from typing import Any

import numpy as np
from numpy.typing import NDArray
from PIL import Image


class ValueNoise:
    """Single-octave noise and fractal (fBm) sums of it, both in [0, 1]."""

    def noise(self, h: int, w: int, cells: float, rng: np.random.Generator) -> NDArray[Any]:
        """Smooth value noise with about `cells` features across the width."""
        gx = max(2, round(cells) + 1)
        gy = max(2, round(cells * h / max(w, 1)) + 1)
        grid = rng.random((gy, gx), dtype=np.float32)
        a = np.asarray(
            Image.fromarray(grid).resize((w, h), Image.Resampling.BICUBIC), dtype=np.float32
        )
        return np.clip(a, 0, 1)

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
        total = np.zeros((h, w), np.float32)
        amp, norm = 1.0, 0.0
        for o in range(octaves):
            total += amp * self.noise(h, w, cells * 2**o, rng)
            norm += amp
            amp *= gain
        return total / norm
