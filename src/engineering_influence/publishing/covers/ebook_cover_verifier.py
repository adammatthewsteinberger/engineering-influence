"""KDP's ebook cover rules (help topics G200645690 and G6GTK3T3NUHKLEFX)."""

from pathlib import Path

import numpy as np
from PIL import Image

from engineering_influence.publishing.covers.ebook_border import EbookBorder
from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec as Kdp


class EbookCoverVerifier:
    """Size, format, colour, compression, and the gray border on a light cover."""

    def run(self, path: Path) -> list[str]:
        """Return problems with the file."""
        problems: list[str] = []
        try:
            with Image.open(path) as probe:
                probe.verify()
            im = Image.open(path)
            im.load()
        except Exception as error:  # noqa: BLE001 - any decode failure means KDP rejects the file
            return [f"{path.name}: not a valid image ({error})"]
        with im:
            if im.format not in ("JPEG", "TIFF"):
                problems.append(f"{path.name}: {im.format}; KDP takes JPEG or TIFF")
            w, h = im.size
            if (w, h) != Kdp.EBOOK_PX:
                problems.append(
                    f"{path.name}: {w} x {h} px; KDP's ideal is {Kdp.EBOOK_PX[0]} x {Kdp.EBOOK_PX[1]}"
                )
            if w < Kdp.EBOOK_MIN_PX[0] or h < Kdp.EBOOK_MIN_PX[1] or max(w, h) > Kdp.EBOOK_MAX_PX:
                problems.append(
                    f"{path.name}: {w} x {h} px is outside KDP's 625 x 1000 to 10,000 px limits"
                )
            if h / w < 1.6 - 1e-9:
                problems.append(
                    f"{path.name}: height to width is {h / w:.3f}; KDP wants at least 1.6"
                )
            if path.stat().st_size >= Kdp.EBOOK_MAX_MB * 1e6:
                problems.append(
                    f"{path.name}: {path.stat().st_size / 1e6:.1f} MB; "
                    f"KDP's limit is {Kdp.EBOOK_MAX_MB} MB"
                )
            if im.mode != "RGB":
                problems.append(
                    f"{path.name}: mode {im.mode}; KDP wants RGB with no alpha and no colour separation"
                )
            if im.info.get("icc_profile"):
                problems.append(f"{path.name}: carries a colour profile")
            if im.format == "TIFF" and im.info.get("compression") not in (None, "raw"):
                problems.append(
                    f"{path.name}: TIFF compressed with {im.info.get('compression')}; "
                    "KDP asks for none"
                )
            if im.format == "JPEG" and im.info.get("progressive"):
                problems.append(f"{path.name}: progressive JPEG; use baseline")
            a = np.asarray(im.convert("RGB"), dtype=np.int16)
            b = Kdp.EBOOK_BORDER_PX
            edge = np.concatenate(
                [
                    a[:b].reshape(-1, 3),
                    a[-b:].reshape(-1, 3),
                    a[:, :b].reshape(-1, 3),
                    a[:, -b:].reshape(-1, 3),
                ]
            )
            bordered = np.abs(edge - np.array(Kdp.EBOOK_BORDER_RGB)).max() <= 12
            if EbookBorder().is_light_edge(im) and not bordered:
                problems.append(
                    f"{path.name}: light background with no gray border; "
                    "KDP recommends a 3 to 4 px medium gray border"
                )
        return problems
