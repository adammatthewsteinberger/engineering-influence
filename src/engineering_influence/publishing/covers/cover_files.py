"""Writes cover images as TIFF, JPEG, and KDP's single-page flattened PDF."""

import io
from pathlib import Path

from PIL import Image

from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec as Kdp


class CoverFiles:
    """File formats KDP accepts."""

    def save_tiff(self, img: Image.Image, path: Path, compress: bool = True) -> None:
        """Print panels use lossless Deflate to keep files small; the ebook cover is
        uncompressed, as KDP asks."""
        img.save(
            path,
            format="TIFF",
            compression="tiff_adobe_deflate" if compress else None,
            dpi=(Kdp.DPI_TAG, Kdp.DPI_TAG),
        )

    def jpeg_bytes(self, img: Image.Image) -> bytes:
        """A high-quality baseline JPEG."""
        buf = io.BytesIO()
        img.save(
            buf,
            format="JPEG",
            quality=97,
            subsampling=0,
            dpi=(Kdp.DPI_TAG, Kdp.DPI_TAG),
            optimize=True,
        )
        return buf.getvalue()

    def write_pdf(
        self,
        img: Image.Image,
        path: Path,
        width_in: float,
        height_in: float,
        title: str,
        author: str,
    ) -> None:
        """A one-page PDF at KDP's exact cover size, holding the art as one flattened RGB image.

        No fonts (the type is part of the image), no transparency, no colour profile, no
        security, and no software credit in the metadata.
        """
        jpg = self.jpeg_bytes(img)
        w_pt, h_pt = width_in * 72, height_in * 72
        content = f"q {w_pt:.4f} 0 0 {h_pt:.4f} 0 0 cm /Im0 Do Q".encode("ascii")

        def text(t: str) -> str:
            return "<FEFF" + t.encode("utf-16-be").hex().upper() + ">"

        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w_pt:.4f} {h_pt:.4f}] "
                "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>"
            ).encode("ascii"),
            (
                f"<< /Type /XObject /Subtype /Image /Width {img.width} /Height {img.height} "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                f"/Length {len(jpg)} >>\nstream\n"
            ).encode("ascii")
            + jpg
            + b"\nendstream",
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"\nendstream",
            f"<< /Title {text(title)} /Author {text(author)} >>".encode("ascii"),
        ]
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, body in enumerate(objects, 1):
            offsets.append(len(out))
            out += f"{i} 0 obj\n".encode("ascii") + body + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii")
        out += b"".join(f"{o:010d} 00000 n \n".encode("ascii") for o in offsets)
        out += (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {len(objects)} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
        path.write_bytes(bytes(out))
