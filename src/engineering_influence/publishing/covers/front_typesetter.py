# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The front-cover title block."""

from typing import Any

from PIL import Image, ImageDraw

from engineering_influence.publishing.covers.cover_layout import CoverLayout
from engineering_influence.publishing.covers.cover_style import CoverStyle
from engineering_influence.publishing.covers.typography import Typography


class FrontTypesetter:
    """Title, subtitle, and author, centred in the front safe area."""

    def __init__(self, typography: Typography) -> None:
        self._t = typography

    def typeset(
        self,
        layer: Image.Image,
        L: CoverLayout,
        st: CoverStyle,
        meta: dict[str, Any],
    ) -> None:
        """Draw onto a transparent text layer."""
        t = self._t
        d = ImageDraw.Draw(layer)
        s = L.front_safe
        x0, y0, x1, y1 = (L.to_px(v) for v in (s.x0, s.y0, s.x1, s.y1))
        sw = x1 - x0
        cx = (x0 + x1) / 2
        lines = [ln.upper() if st.title_case_upper else ln for ln in st.title_lines]
        size = t.fit_size(st.title_font, lines, st.title_tracking, sw * st.title_frac)
        tf = t.font(st.title_font, size)
        lead = size * (1.02 if st.title_case_upper else 0.98)
        author = meta["author"].upper()
        af = t.font(st.author_font, L.to_px(0.115))
        a_track = st.author_tracking * af.size
        aw = t.tracked_width(af, author, a_track)
        sub = meta.get("subtitle", "")
        serif_sub = bool(st.extra.get("subtitle_serif", "Cormorant" in st.subtitle_font))
        sub_size = L.to_px(0.205 if serif_sub else 0.112)
        sub_text = sub if serif_sub else sub.upper()
        sf = t.font(st.subtitle_font, sub_size)
        sub_track = 0 if serif_sub else 0.22 * sub_size
        sub_lines = t.wrap_px(sub_text, sf, sw * 0.86, sub_track)

        y = y0
        if st.author_on_top:
            t.draw_tracked(d, (cx - aw / 2, y), author, af, t.c8(st.author_color), a_track)
            y += af.size * 2.6
        else:
            y += L.to_px(st.title_top * L.front.h)
        for ln in lines:
            w = t.tracked_width(tf, ln, st.title_tracking * size)
            t.draw_tracked(
                d,
                (cx - w / 2, y - t.cap_top(tf, ln)),
                ln,
                tf,
                t.c8(st.title_color),
                st.title_tracking * size,
            )
            y += lead
        y += sub_size * 0.35
        for ln in sub_lines:
            w = t.tracked_width(sf, ln, sub_track)
            t.draw_tracked(d, (cx - w / 2, y), ln, sf, t.c8(st.subtitle_color), sub_track)
            y += sub_size * 1.25
        if not st.author_on_top:
            # An optional lift keeps descending capitals (Q, J) inside the safe area.
            ay = y1 - af.size - L.to_px(float(st.extra.get("author_lift_in", 0.0)))
            t.draw_tracked(d, (cx - aw / 2, ay), author, af, t.c8(st.author_color), a_track)
