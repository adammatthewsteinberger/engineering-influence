"""KDP: a light cover can vanish against the white store page, so it gets a gray frame."""

import numpy as np
from PIL import Image, ImageDraw

from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec as Kdp


class EbookBorder:
    """Detects a light edge and frames the cover in medium gray."""

    def is_light_edge(self, img: Image.Image, inset: int = 4, band: int = 24) -> bool:
        """True when the outer band of the picture is near white (Rec. 709 luminance > 0.8)."""
        a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255
        lum = a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        h, w = lum.shape
        ring = np.ones_like(lum, dtype=bool)
        ring[inset + band : h - inset - band, inset + band : w - inset - band] = False
        ring[:inset, :] = ring[-inset:, :] = ring[:, :inset] = ring[:, -inset:] = False
        return float(lum[ring].mean()) > 0.8

    def add(self, img: Image.Image) -> Image.Image:
        """A copy of the image with the border drawn on."""
        out = img.copy()
        ImageDraw.Draw(out).rectangle(
            (0, 0, out.width - 1, out.height - 1),
            outline=Kdp.EBOOK_BORDER_RGB,
            width=Kdp.EBOOK_BORDER_PX,
        )
        return out
