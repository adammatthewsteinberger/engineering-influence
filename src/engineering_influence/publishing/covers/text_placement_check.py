# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every inked text pixel sits in a safe area and clear of the barcode."""

import numpy as np
from PIL import Image

from engineering_influence.publishing.covers.cover_layout import CoverLayout


class TextPlacementCheck:
    """Checks the transparent text layer against the layout."""

    def run(self, layer: Image.Image, L: CoverLayout) -> list[str]:
        """Return a problem for stray text and for text over the barcode."""
        alpha = np.asarray(layer.getchannel("A")) > 8
        allowed = np.zeros_like(alpha)
        tol = round(0.03 * L.ppi)  # glyph overhang and anti-aliasing, well inside KDP's limits
        for b in (L.front_safe, L.back_safe, L.spine_safe):
            if b is not None:
                x0, y0, x1, y1 = L.box_px(b)
                allowed[max(0, y0 - tol) : y1 + tol, max(0, x0 - tol) : x1 + tol] = True
        problems = []
        stray = alpha & ~allowed
        if stray.any():
            ys, xs = np.nonzero(stray)
            problems.append(
                f"{stray.sum()} text pixels outside the safe areas, "
                f"e.g. at ({xs[0] / L.ppi:.2f} in, {ys[0] / L.ppi:.2f} in)"
            )
        if L.barcode is not None:
            x0, y0, x1, y1 = L.box_px(L.barcode)
            if alpha[y0:y1, x0:x1].any():
                problems.append("text inside the barcode area")
        return problems
