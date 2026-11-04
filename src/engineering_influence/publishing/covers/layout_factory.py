# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""KDP layouts for the ebook cover, the paperback wrap, and the hardcover wrap."""

from engineering_influence.publishing.covers.box import Box
from engineering_influence.publishing.covers.cover_layout import CoverLayout
from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec as Kdp


class LayoutFactory:
    """Spine width follows page count; the back cover keeps a clear barcode box."""

    def ebook(self) -> CoverLayout:
        """The 1600 x 2560 px Kindle cover."""
        ppi = Kdp.EBOOK_PX[0] / Kdp.TRIM_W
        height = Kdp.EBOOK_PX[1] / ppi
        front = Box(0, 0, Kdp.TRIM_W, height)
        return CoverLayout("ebook", Kdp.TRIM_W, height, ppi, front, front.inset(0.42, 0.5))

    def paperback(self, pages: int) -> CoverLayout:
        """Back + spine + front with bleed."""
        spine_w = pages * Kdp.PAPER_WHITE
        width = 2 * Kdp.BLEED + 2 * Kdp.TRIM_W + spine_w
        height = 2 * Kdp.BLEED + Kdp.TRIM_H
        back = Box(Kdp.BLEED, Kdp.BLEED, Kdp.BLEED + Kdp.TRIM_W, Kdp.BLEED + Kdp.TRIM_H)
        spine = Box(back.x1, Kdp.BLEED, back.x1 + spine_w, Kdp.BLEED + Kdp.TRIM_H)
        front = Box(spine.x1, Kdp.BLEED, spine.x1 + Kdp.TRIM_W, Kdp.BLEED + Kdp.TRIM_H)
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
        spine_w = pages * Kdp.PAPER_WHITE + Kdp.HC_SPINE_EXTRA
        bw, bh = Kdp.TRIM_W + Kdp.HC_BOARD_W, Kdp.TRIM_H + Kdp.HC_BOARD_H
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
