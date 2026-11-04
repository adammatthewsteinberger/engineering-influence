# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Structural PDF checks: size, bookmarks, annotations, transparency, fonts."""

from typing import Any

from pypdf import PdfReader

from engineering_influence.publishing.kdp_geometry import KdpGeometry


class PdfStructureCheck:
    """Reads the finished PDF so nothing is taken on trust."""

    def run(self, reader: PdfReader) -> list[str]:
        """Return a problem for each structural violation."""
        geometry = KdpGeometry()
        problems: list[str] = []
        if reader.outline:
            problems.append("PDF has bookmarks; KDP print interiors should not")
        unembedded: set[str] = set()
        for index, page in enumerate(reader.pages):
            width, height = float(page.mediabox.width), float(page.mediabox.height)
            if (
                abs(width - geometry.TRIM[0]) > geometry.TOLERANCE
                or abs(height - geometry.TRIM[1]) > geometry.TOLERANCE
            ):
                problems.append(
                    f"page {index + 1} is {width:.1f} x {height:.1f} pt, expected 432 x 648"
                )
            if "/Annots" in page:
                problems.append(f"page {index + 1} has annotations or links")
            if "/Group" in page:
                problems.append(f"page {index + 1} has a transparency group")
            unembedded |= self._unembedded_fonts(page)
        problems.extend(f"font not embedded: {name}" for name in sorted(unembedded))
        return problems

    def _unembedded_fonts(self, page: Any) -> set[str]:
        resources = page.get("/Resources")
        fonts = resources.get_object().get("/Font") if resources else None
        missing: set[str] = set()
        if not fonts:
            return missing
        for name, reference in fonts.get_object().items():
            font = reference.get_object()
            descendants = [font]
            if "/DescendantFonts" in font:
                descendants = [item.get_object() for item in font["/DescendantFonts"]]
            for descendant in descendants:
                descriptor = descendant.get("/FontDescriptor")
                if descriptor is None:
                    continue
                descriptor = descriptor.get_object()
                if not any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")):
                    missing.add(str(descendant.get("/BaseFont", name)))
        return missing
