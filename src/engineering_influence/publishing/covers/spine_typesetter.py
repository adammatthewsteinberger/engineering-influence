"""Spine text, set horizontally and rotated to read top to bottom."""

from typing import Any

from PIL import Image, ImageDraw

from engineering_influence.publishing.covers.cover_layout import CoverLayout
from engineering_influence.publishing.covers.cover_style import CoverStyle
from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec as Kdp
from engineering_influence.publishing.covers.typography import Typography


class SpineTypesetter:
    """Title and author surname, when the book is thick enough to carry them."""

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
        if L.spine_safe is None:  # ebook, or a book too thin for spine text
            return
        s = L.spine_safe
        sw, sh = L.to_px(s.w), L.to_px(s.h)
        # A narrow proof spine cannot hold a readable title. Leave it blank rather than violate
        # the print-cover minimum or produce illegible microtype.
        if L.kind != "ebook" and sw * 0.50 < L.to_px(Kdp.TEXT_FLOOR_IN):
            return
        strip = Image.new("RGBA", (int(sh), int(sw)), (0, 0, 0, 0))
        d = ImageDraw.Draw(strip)
        title = " ".join(st.title_lines)
        title = title.upper() if st.title_case_upper else title
        tsize = min(sw * 0.50, 400)
        tf = t.font(st.spine_font, tsize)
        track = st.title_tracking * tsize * 0.8
        surname = meta["author"].split()[-1].upper()
        af = t.font(st.author_font, t.floor_px(L, tsize * 0.48))
        a_track = 0.30 * af.size
        tw = t.tracked_width(tf, title, track)
        aw = t.tracked_width(af, surname, a_track)
        gap = sw * 0.9
        total = tw + gap + aw
        if total > sh:
            scale = (sh - aw - gap) / tw
            tf = t.font(st.spine_font, tsize * scale)
            track *= scale
            tw = t.tracked_width(tf, title, track)
        cy = sw / 2
        tb = tf.getbbox(title)
        ab = af.getbbox(surname)
        t.draw_tracked(d, (0, cy - (tb[1] + tb[3]) / 2), title, tf, t.c8(st.spine_color), track)
        t.draw_tracked(
            d, (sh - aw, cy - (ab[1] + ab[3]) / 2), surname, af, t.c8(st.author_color), a_track
        )
        rot = strip.rotate(-90, expand=True)
        layer.alpha_composite(rot, (int(L.to_px(s.x0)), int(L.to_px(s.y0))))
