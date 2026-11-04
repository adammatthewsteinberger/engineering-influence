"""Reads the page number printed on a PDF page."""

import re
from typing import Any

from engineering_influence.publishing.kdp_geometry import KdpGeometry


class FolioReader:
    """Finds the folio in the running head or the opener footer."""

    def read(self, page: Any) -> str | None:
        """Return the printed folio, or None when the page prints none.

        The running-head folio sits about 0.43 in from the top and the opener folio about
        0.57 in from the bottom. The text block starts 0.85 in from the top and ends 0.9 in
        from the bottom, so these zones never hold body text.
        """
        pt = KdpGeometry.POINTS_PER_INCH
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
        candidates = [
            word
            for word in words
            if (word["bottom"] < 0.7 * pt or word["top"] > page.height - 0.75 * pt)
            and re.fullmatch(r"\d+|[ivxlc]+", word["text"])
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda word: word["top"])
        return str(candidates[0]["text"])
