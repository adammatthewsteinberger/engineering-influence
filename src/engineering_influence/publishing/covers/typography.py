"""Text measuring and drawing shared by the front, back, and spine typesetters."""

import re
from typing import Any

from PIL import ImageDraw, ImageFont

from engineering_influence.publishing.covers.cover_layout import CoverLayout
from engineering_influence.publishing.covers.font_loader import FontLoader
from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec as Kdp
from engineering_influence.publishing.covers.text_recorder import TextRecorder


class Typography:
    """Tracked (letter-spaced) text, fitting, wrapping, and the print size floor."""

    def __init__(self, fonts: FontLoader, recorder: TextRecorder) -> None:
        self.fonts = fonts
        self.recorder = recorder

    def font(self, name: str, size_px: float) -> ImageFont.FreeTypeFont:
        """Load a font."""
        return self.fonts.load(name, size_px)

    def floor_px(self, layout: CoverLayout, size_px: float) -> float:
        """Raise a print text size to the floor; ebook covers are not printed."""
        if layout.kind == "ebook":
            return size_px
        return max(size_px, layout.to_px(Kdp.TEXT_FLOOR_IN))

    def c8(self, color: tuple[float, float, float]) -> tuple[int, int, int, int]:
        """A 0..1 colour as an opaque 8-bit RGBA tuple."""
        r, g, b = (int(max(0, min(255, round(v * 255)))) for v in color)
        return (r, g, b, 255)

    def tracked_width(self, f: ImageFont.FreeTypeFont, text: str, tracking_px: float) -> float:
        """Width of text with extra spacing between characters."""
        if tracking_px == 0:
            return f.getlength(text)
        return sum(f.getlength(ch) for ch in text) + tracking_px * (len(text) - 1)

    def draw_tracked(
        self,
        draw: ImageDraw.ImageDraw,
        xy: tuple[float, float],
        text: str,
        f: ImageFont.FreeTypeFont,
        fill: tuple[int, int, int, int],
        tracking_px: float,
    ) -> None:
        """Draw tracked text and record its size."""
        self.recorder.record(int(f.size))
        x, y = xy
        if tracking_px == 0:
            draw.text((x, y), text, font=f, fill=fill)
            return
        for ch in text:
            draw.text((x, y), ch, font=f, fill=fill)
            x += f.getlength(ch) + tracking_px

    def fit_size(
        self, fontname: str, lines: list[str], tracking_em: float, width_px: float
    ) -> float:
        """The font size at which the widest line is `width_px` wide."""
        size = 400.0
        f = self.font(fontname, size)
        widest = max(self.tracked_width(f, ln, tracking_em * size) for ln in lines)
        return size * width_px / widest

    def cap_top(self, f: ImageFont.FreeTypeFont, text: str) -> int:
        """The offset from the draw origin to the top of the text's ink."""
        return int(f.getbbox(text)[1])

    def wrap_px(
        self, text: str, f: ImageFont.FreeTypeFont, width: float, tracking: float = 0
    ) -> list[str]:
        """Greedy word wrap to a pixel width."""
        words, lines, cur = text.split(), [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if self.tracked_width(f, trial, tracking) <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def plain(self, md: str) -> str:
        """Strip Markdown emphasis markers."""
        return re.sub(r"[*_`]", "", md)


Meta = dict[str, Any]
