# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A power-law starfield."""

from typing import Any

import numpy as np
from numpy.typing import NDArray

from engineering_influence.publishing.covers.box_blur import BoxBlur
from engineering_influence.publishing.covers.compositing import Compositing


class Starfield:
    """Brightness follows a power law, with a slight colour-temperature spread."""

    def add(
        self,
        img: NDArray[Any],
        rng: np.random.Generator,
        density_per_sq_in: float,
        ppi: float,
        weight: NDArray[Any] | None = None,
        max_gain: float = 1.0,
    ) -> None:
        """Add stars to `img` in place."""
        h, w = img.shape[:2]
        n = int(density_per_sq_in * (w / ppi) * (h / ppi))
        xs = rng.random(n) * (w - 1)
        ys = rng.random(n) * (h - 1)
        b = np.clip(rng.pareto(2.6, n) * 0.18, 0, 1.0).astype(np.float32)
        field_ = np.zeros((h, w), np.float32)
        xi, yi = xs.astype(int), ys.astype(int)
        np.add.at(field_, (yi, xi), b)
        blur = BoxBlur()
        core = blur.apply(field_, ppi / 300 * 0.6) * 2.2
        halo = blur.apply(field_, ppi / 300 * 2.2) * 1.6
        s = np.clip(core + halo * 0.6, 0, 1.4) * max_gain
        if weight is not None:
            s *= weight
        img += s[..., None] * Compositing().rgb(0.92, 0.94, 1.0)
