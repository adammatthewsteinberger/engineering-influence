# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""KDP's print cover rules (help topics G201953020 and GDTKFJPNQCBTMRV6)."""

from pathlib import Path

from pypdf import PdfReader

from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec as Kdp


class PrintPdfVerifier:
    """A single unencrypted page of exact size holding one flattened RGB image."""

    def run(self, path: Path, width_in: float, height_in: float) -> list[str]:
        """Return problems with the PDF."""
        problems: list[str] = []
        try:
            r = PdfReader(str(path))
        except Exception as error:  # noqa: BLE001
            return [f"{path.name}: not a readable PDF ({error})"]
        if r.is_encrypted:  # its pages cannot be read, so there is nothing more to check
            return [f"{path.name}: encrypted; KDP rejects secured files"]
        if len(r.pages) != 1:
            problems.append(f"{path.name}: {len(r.pages)} pages; KDP wants a single page")
        page = r.pages[0]
        w_in, h_in = float(page.mediabox.width) / 72, float(page.mediabox.height) / 72
        if abs(w_in - width_in) > 0.001 or abs(h_in - height_in) > 0.001:
            problems.append(
                f"{path.name}: page {w_in:.4f} x {h_in:.4f} in, "
                f"expected {width_in:.4f} x {height_in:.4f} in"
            )
        res = page.get("/Resources", {})
        if "/Font" in res:
            problems.append(f"{path.name}: uses fonts; the type should be flattened into the art")
        if "/Group" in page:
            problems.append(
                f"{path.name}: has a transparency group; KDP wants transparency flattened"
            )
        images = [x.get_object() for x in res.get("/XObject", {}).values()]
        if not images:
            problems.append(f"{path.name}: holds no image")
        for im in images:
            if im.get("/Subtype") != "/Image":
                problems.append(f"{path.name}: holds a non-image object")
                continue
            if im.get("/ColorSpace") != "/DeviceRGB":
                problems.append(
                    f"{path.name}: image colour space {im.get('/ColorSpace')}; "
                    "one plain colour space expected"
                )
            if "/SMask" in im or "/Mask" in im:
                problems.append(f"{path.name}: image has transparency")
            dpi_x, dpi_y = int(im["/Width"]) / width_in, int(im["/Height"]) / height_in
            if min(dpi_x, dpi_y) < 300 - 1e-6:
                problems.append(
                    f"{path.name}: image is {min(dpi_x, dpi_y):.2f} DPI; KDP's minimum is 300"
                )
        if path.stat().st_size > Kdp.PDF_MAX_MB * 1e6:
            problems.append(
                f"{path.name}: {path.stat().st_size / 1e6:.1f} MB; "
                f"KDP recommends {Kdp.PDF_MAX_MB} MB or less"
            )
        return problems
