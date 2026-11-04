# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pixel size, DPI tag, and colour mode of a cover TIFF or JPEG."""

import math
from pathlib import Path

from PIL import Image

from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec as Kdp


class ImageVerifier:
    """Checks a print panel against the exact KDP page size."""

    def run(self, path: Path, width_in: float, height_in: float, ppi: float) -> list[str]:
        """Return problems with the file."""
        problems: list[str] = []
        with Image.open(path) as im:
            want = (math.ceil(width_in * ppi - 1e-6), math.ceil(height_in * ppi - 1e-6))
            if abs(im.size[0] - want[0]) > 1 or abs(im.size[1] - want[1]) > 1:
                problems.append(f"{path.name}: {im.size} px, expected {want}")
            dpi = im.info.get("dpi", (0, 0))
            if abs(float(dpi[0]) - Kdp.DPI_TAG) > 0.5 or abs(float(dpi[1]) - Kdp.DPI_TAG) > 0.5:
                problems.append(f"{path.name}: tagged {dpi} DPI, expected {Kdp.DPI_TAG}")
            if im.mode != "RGB":
                problems.append(f"{path.name}: mode {im.mode}, expected RGB with no alpha")
            if im.info.get("icc_profile"):
                problems.append(f"{path.name}: carries a colour profile")
        return problems
