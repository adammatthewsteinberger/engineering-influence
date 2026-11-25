# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The built-in painter: a deep vertical gradient with soft texture and film grain."""

from typing import Any

import numpy as np
from numpy.typing import NDArray

from engineering_influence.infrastructure.covers.compositing import Compositing
from engineering_influence.infrastructure.covers.film_grain import FilmGrain
from engineering_influence.infrastructure.covers.quiet_zone import QuietZone
from engineering_influence.infrastructure.covers.value_noise import ValueNoise
from engineering_influence.interfaces.cover_painter_interface import CoverPainterInterface
from engineering_influence.models.covers.cover_layout import CoverLayout
from engineering_influence.models.covers.cover_style import CoverStyle


class GradientPainter(CoverPainterInterface):
    """Needs no private art. Colours come from style.extra["top"] and ["bottom"]."""

    TOP = (0.10, 0.15, 0.27)
    BOTTOM = (0.02, 0.03, 0.08)

    def paint(self, layout: CoverLayout, style: CoverStyle) -> NDArray[Any]:
        """A seeded, reproducible gradient that recedes behind the back-cover text."""
        width, height = layout.px
        rng = np.random.default_rng(style.seed)
        comp = Compositing()
        top = comp.rgb(*style.extra.get("top", self.TOP))
        bottom = comp.rgb(*style.extra.get("bottom", self.BOTTOM))
        t = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
        img = np.broadcast_to(comp.mix(top, bottom, t), (height, width, 3)).astype(np.float32)
        texture = ValueNoise().fbm(height, width, 3, 4, rng)
        quiet = QuietZone().mask(layout, height, width)
        img = img + ((texture - 0.5) * 0.06 * (1 - quiet))[..., None]
        FilmGrain().add(img, rng, 0.012)
        return np.asarray(img, dtype=np.float32)
