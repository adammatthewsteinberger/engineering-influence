# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""KDP layouts for the ebook cover, the paperback wrap, and the hardcover wrap."""

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.models.covers.box import Box
from engineering_influence.models.covers.cover_layout import CoverLayout
from engineering_influence.models.covers.interfaces.layout_factory_interface import (
    LayoutFactoryInterface,
)
from engineering_influence.models.covers.kdp_cover_spec import KdpCoverSpec as Kdp
from engineering_influence.models.typesetting.paper_stock import PaperStock
from engineering_influence.models.typesetting.trim_size import TrimSize


class LayoutFactory(LayoutFactoryInterface):
    """Spine width follows page count and paper; the back cover keeps a clear barcode box.

    With no arguments the layouts are for a 6 x 9 in book on white paper.
    """

    def __init__(self, trim: TrimSize | None = None, paper: PaperStock | None = None) -> None:
        self._trim = trim or TrimSize.for_name(None)
        self._paper = paper or PaperStock.for_name(None)

    def ebook(self) -> CoverLayout:
        """The 1600 x 2560 px Kindle cover."""
        ppi = Kdp.EBOOK_PX[0] / self._trim.width_in
        height = Kdp.EBOOK_PX[1] / ppi
        front = Box(0, 0, self._trim.width_in, height)
        return CoverLayout("ebook", self._trim.width_in, height, ppi, front, front.inset(0.42, 0.5))

    def paperback(self, pages: int) -> CoverLayout:
        """Back + spine + front with bleed."""
        spine_w = pages * self._paper.inches_per_page
        width = 2 * Kdp.BLEED + 2 * self._trim.width_in + spine_w
        height = 2 * Kdp.BLEED + self._trim.height_in
        back = Box(
            Kdp.BLEED, Kdp.BLEED, Kdp.BLEED + self._trim.width_in, Kdp.BLEED + self._trim.height_in
        )
        spine = Box(back.x1, Kdp.BLEED, back.x1 + spine_w, Kdp.BLEED + self._trim.height_in)
        front = Box(
            spine.x1, Kdp.BLEED, spine.x1 + self._trim.width_in, Kdp.BLEED + self._trim.height_in
        )
        barcode = Box(
            back.x1 - 0.25 - Kdp.BARCODE_W,
            back.y1 - 0.25 - Kdp.BARCODE_H,
            back.x1 - 0.25,
            back.y1 - 0.25,
        )
        spine_safe = spine.inset(0.0625, 0.45) if pages >= Kdp.SPINE_TEXT_MIN_PAGES else None
        return CoverLayout(
            "paperback",
            width,
            height,
            Kdp.PPI,
            front,
            front.inset(0.5, 0.55),
            back,
            back.inset(0.55, 0.6),
            spine,
            spine_safe,
            barcode,
        )

    def hardcover(self, pages: int) -> CoverLayout:
        """Case laminate: boards, hinge, spine, and a 15 mm wrap."""
        if not self._trim.hardcover:
            raise ManuscriptError(f"KDP does not print a hardcover at the {self._trim.name} trim")
        spine_w = pages * self._paper.inches_per_page + Kdp.HC_SPINE_EXTRA
        bw, bh = self._trim.width_in + Kdp.HC_BOARD_W, self._trim.height_in + Kdp.HC_BOARD_H
        width = 2 * Kdp.HC_WRAP + 2 * bw + spine_w
        height = 2 * Kdp.HC_WRAP + bh
        back = Box(Kdp.HC_WRAP, Kdp.HC_WRAP, Kdp.HC_WRAP + bw, Kdp.HC_WRAP + bh)
        spine = Box(back.x1, Kdp.HC_WRAP, back.x1 + spine_w, Kdp.HC_WRAP + bh)
        front = Box(spine.x1, Kdp.HC_WRAP, spine.x1 + bw, Kdp.HC_WRAP + bh)
        # Text stays clear of the hinge on the spine side and 0.5 in inside the board edges.
        front_safe = Box(
            front.x0 + Kdp.HC_HINGE + 0.25, front.y0 + 0.6, front.x1 - 0.5, front.y1 - 0.6
        )
        back_safe = Box(back.x0 + 0.6, back.y0 + 0.65, back.x1 - Kdp.HC_HINGE - 0.3, back.y1 - 0.65)
        barcode = Box(
            back.x1 - Kdp.HC_HINGE - 0.25 - Kdp.BARCODE_W,
            height - 0.76 - Kdp.BARCODE_H,
            back.x1 - Kdp.HC_HINGE - 0.25,
            height - 0.76,
        )
        spine_safe = spine.inset(0.0625, 0.5) if pages >= Kdp.SPINE_TEXT_MIN_PAGES else None
        return CoverLayout(
            "hardcover",
            width,
            height,
            Kdp.PPI,
            front,
            front_safe,
            back,
            back_safe,
            spine,
            spine_safe,
            barcode,
        )
