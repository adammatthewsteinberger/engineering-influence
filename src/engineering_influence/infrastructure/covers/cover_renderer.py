# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Paints, dithers, typesets, and checks one cover image."""

from typing import Any

import numpy as np
from PIL import Image

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.covers.back_typesetter import BackTypesetter
from engineering_influence.infrastructure.covers.font_loader import FontLoader
from engineering_influence.infrastructure.covers.front_typesetter import FrontTypesetter
from engineering_influence.infrastructure.covers.interfaces.cover_renderer_interface import (
    CoverRendererInterface,
)
from engineering_influence.infrastructure.covers.painter_registry import PainterRegistry
from engineering_influence.infrastructure.covers.spine_typesetter import SpineTypesetter
from engineering_influence.infrastructure.covers.text_placement_check import TextPlacementCheck
from engineering_influence.infrastructure.covers.typography import Typography
from engineering_influence.models.covers.cover_layout import CoverLayout
from engineering_influence.models.covers.cover_style import CoverStyle
from engineering_influence.models.covers.kdp_cover_spec import KdpCoverSpec as Kdp
from engineering_influence.models.covers.layout_check import LayoutCheck
from engineering_influence.models.covers.text_recorder import TextRecorder


class CoverRenderer(CoverRendererInterface):
    """Painter output plus ordered dither, then front, back, and spine text on a layer."""

    def __init__(
        self,
        registry: PainterRegistry,
        fonts: FontLoader,
        min_text_pt: float = Kdp.MIN_TEXT_PT,
    ) -> None:
        self._registry = registry
        self._fonts = fonts
        self._min_text_pt = min_text_pt

    def render(self, L: CoverLayout, st: CoverStyle, meta: dict[str, Any]) -> Image.Image:
        """Return the finished RGB cover, or fail when the text or layout breaks a KDP rule."""
        arr = np.clip(self._registry.get(st.painter).paint(L, st), 0, 1)
        rng = np.random.default_rng(st.seed + 7)
        arr = arr * 255 + (rng.random(arr.shape[:2], dtype=np.float32)[..., None] - 0.5)  # dither
        base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
        layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        recorder = TextRecorder()
        typography = Typography(self._fonts, recorder)
        FrontTypesetter(typography).typeset(layer, L, st, meta)
        BackTypesetter(typography).typeset(layer, L, st, meta)
        SpineTypesetter(typography).typeset(layer, L, st, meta)
        problems = TextPlacementCheck().run(layer, L) + LayoutCheck().run(L)
        smallest = recorder.smallest()
        if L.kind != "ebook" and smallest is not None and smallest / L.ppi * 72 < self._min_text_pt:
            problems.append(
                f"text set at {smallest / L.ppi * 72:.1f} pt; KDP's minimum is {self._min_text_pt:g} pt"
            )
        if problems:
            raise BookBuildError(f"[{L.kind}] cover text check failed: " + "; ".join(problems))
        base.alpha_composite(layer)
        return base.convert("RGB")
