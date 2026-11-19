# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Structural PDF checks: size, bookmarks, annotations, transparency, fonts."""

from engineering_influence.models.publishing.pdf_document import PdfDocument
from engineering_influence.services.publishing.kdp_geometry import KdpGeometry


class PdfStructureCheck:
    """Applies the KDP structure rules to the facts of a finished PDF."""

    def run(self, document: PdfDocument) -> list[str]:
        """Return a problem for each structural violation."""
        geometry = KdpGeometry()
        problems: list[str] = []
        if document.has_outline:
            problems.append("PDF has bookmarks; KDP print interiors should not")
        unembedded: set[str] = set()
        for index, page in enumerate(document.pages):
            width, height = page.media_width, page.media_height
            if (
                abs(width - geometry.TRIM[0]) > geometry.TOLERANCE
                or abs(height - geometry.TRIM[1]) > geometry.TOLERANCE
            ):
                problems.append(
                    f"page {index + 1} is {width:.1f} x {height:.1f} pt, expected 432 x 648"
                )
            if page.has_annotations:
                problems.append(f"page {index + 1} has annotations or links")
            if page.has_group:
                problems.append(f"page {index + 1} has a transparency group")
            unembedded |= page.unembedded_fonts
        problems.extend(f"font not embedded: {name}" for name in sorted(unembedded))
        return problems
