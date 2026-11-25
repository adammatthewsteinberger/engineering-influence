# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The back-cover blurb, author note, and imprint."""

from typing import Any

from PIL import Image, ImageDraw, ImageFont

from engineering_influence.errors.typesetting.back_cover_text_too_long_error import (
    BackCoverTextTooLongError,
)
from engineering_influence.infrastructure.covers.interfaces.back_typesetter_interface import (
    BackTypesetterInterface,
)
from engineering_influence.infrastructure.covers.typography import Typography
from engineering_influence.models.covers.cover_layout import CoverLayout
from engineering_influence.models.covers.cover_style import CoverStyle

Block = tuple[str, ImageFont.FreeTypeFont, list[str], float, float]


class BackTypesetter(BackTypesetterInterface):
    """Lays the description out above the barcode, shrinking it until it fits.

    If it still does not fit at the smallest type it raises ``BackCoverTextTooLongError`` instead
    of drawing text into the barcode area, which KDP keeps clear.
    """

    def __init__(self, typography: Typography) -> None:
        self._t = typography

    def typeset(
        self,
        layer: Image.Image,
        L: CoverLayout,
        st: CoverStyle,
        meta: dict[str, Any],
    ) -> None:
        """Draw onto a transparent text layer; ebook covers have no back."""
        t = self._t
        if L.back_safe is None or L.barcode is None:
            return
        d = ImageDraw.Draw(layer)
        s = L.back_safe
        x0, y0, x1, y1 = (L.to_px(v) for v in (s.x0, s.y0, s.x1, s.y1))
        width = x1 - x0
        barcode_top = L.to_px(L.barcode.y0) - L.to_px(0.25)
        paras = [
            p.strip()
            for p in t.plain(meta.get("description", "")).strip().split("\n\n")
            if p.strip()
        ]
        bio = t.plain(meta.get("author_bio", "")).strip().split("\n\n")
        bio_text = " ".join(p.strip() for p in bio[:1])
        site = meta.get("website", "").replace("https://", "").replace("http://", "")

        size = L.to_px(0.158)
        blocks, bottom = self._lay_out(L, st, paras, bio_text, width, y0, size)
        while bottom > barcode_top and size > L.to_px(0.11):
            size *= 0.97
            blocks, bottom = self._lay_out(L, st, paras, bio_text, width, y0, size)
        if bottom > barcode_top:
            raise BackCoverTextTooLongError(
                characters=sum(len(p) for p in paras),
                capacity=self._capacity(L, st, paras, bio_text, width, y0, size, barcode_top),
                overflow_in=(bottom - barcode_top) / L.ppi,
            )
        # Centre the block in the space above the barcode, leaning slightly high.
        shift = max(0.0, (barcode_top - bottom) * 0.42)
        for kind, f_, ls, y, lh in blocks:
            y += shift
            if kind == "label":
                t.draw_tracked(d, (x0, y), ls[0], f_, t.c8(st.accent), 0.3 * f_.size)
                continue
            for i, ln in enumerate(ls):
                t.recorder.record(int(f_.size))
                d.text((x0, y + i * lh), ln, font=f_, fill=t.c8(st.body_color))
        # Imprint, at the bottom left beside the barcode area.
        pf = t.font(st.author_font, t.floor_px(L, L.to_px(0.085)))
        imprint = meta["publisher"].upper()
        py = y1 - pf.size * 2.9
        t.draw_tracked(d, (x0, py), imprint, pf, t.c8(st.body_color), 0.28 * pf.size)
        if site:
            sf = t.font(st.author_font, t.floor_px(L, L.to_px(0.085)))
            t.draw_tracked(d, (x0, py + pf.size * 1.6), site, sf, t.c8(st.accent), 0.06 * sf.size)

    def _capacity(
        self,
        L: CoverLayout,
        st: CoverStyle,
        paras: list[str],
        bio_text: str,
        width: float,
        y0: float,
        size: float,
        barcode_top: float,
    ) -> int:
        """How many characters of the description fit above the barcode at this type size."""
        low, high = 0, sum(len(p) for p in paras)
        while low < high:
            middle = (low + high + 1) // 2
            kept = self._first_characters(paras, middle)
            _, bottom = self._lay_out(L, st, kept, bio_text, width, y0, size)
            if bottom <= barcode_top:
                low = middle
            else:
                high = middle - 1
        return low

    @staticmethod
    def _first_characters(paras: list[str], count: int) -> list[str]:
        kept: list[str] = []
        for paragraph in paras:
            if count <= 0:
                break
            kept.append(paragraph[:count])
            count -= len(paragraph)
        return kept

    def _lay_out(
        self,
        L: CoverLayout,
        st: CoverStyle,
        paras: list[str],
        bio_text: str,
        width: float,
        y0: float,
        size: float,
    ) -> tuple[list[Block], float]:
        t = self._t
        bf = t.font(st.body_font, size)
        hf = t.font(st.body_italic, size * 1.22)
        blocks: list[Block] = []
        y = y0
        first = True
        for p in paras:
            f_ = hf if first else bf
            lh = f_.size * (1.30 if first else 1.42)
            ls = t.wrap_px(p, f_, width)
            blocks.append(("text", f_, ls, y, lh))
            y += lh * len(ls) + size * 0.85
            first = False
        y += size * 0.9
        af = t.font(st.author_font, t.floor_px(L, size * 0.62))
        blocks.append(("label", af, ["ABOUT THE AUTHOR"], y, af.size))
        y += af.size * 2.2
        ls = t.wrap_px(bio_text, bf, width)
        lh = size * 1.36
        blocks.append(("text", bf, ls, y, lh))
        y += lh * len(ls)
        return blocks, y
