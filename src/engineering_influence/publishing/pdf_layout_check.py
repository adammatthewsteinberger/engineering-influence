# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Layout checks: margins, blank-page runs; also collects page text and folios."""

from typing import Any

from engineering_influence.publishing.folio_reader import FolioReader
from engineering_influence.publishing.kdp_geometry import KdpGeometry


class PdfLayoutCheck:
    """Walks pdfplumber pages and reports margin and blank-page violations."""

    def run(self, pages: list[Any]) -> tuple[list[str], list[str], list[str | None]]:
        """Return (problems, page texts, printed folios)."""
        geometry = KdpGeometry()
        count = len(pages)
        gutter_in = geometry.gutter_inches(count)
        gutter_min = gutter_in * geometry.POINTS_PER_INCH
        reader = FolioReader()
        problems: list[str] = []
        texts: list[str] = []
        folios: list[str | None] = []
        blank_run = 0
        for index, page in enumerate(pages):
            texts.append(page.extract_text(x_tolerance=1.5) or "")
            folios.append(reader.read(page))
            chars = page.chars
            if not chars:
                blank_run += 1
                if blank_run > 2:
                    problems.append(
                        f"more than two consecutive blank pages ending at page {index + 1}"
                    )
                continue
            blank_run = 0
            x0 = min(c["x0"] for c in chars)
            x1 = max(c["x1"] for c in chars)
            top = min(c["top"] for c in chars)
            bottom = max(c["bottom"] for c in chars)
            recto = index % 2 == 0
            inside = x0 if recto else page.width - x1
            outside = page.width - x1 if recto else x0
            tol = geometry.TOLERANCE
            if inside + tol < gutter_min:
                problems.append(
                    f"page {index + 1}: text {inside / geometry.POINTS_PER_INCH:.3f} in from the "
                    f"gutter (KDP minimum {gutter_in} in for {count} pages)"
                )
            if outside + tol < geometry.OUTER_MIN:
                problems.append(
                    f"page {index + 1}: text {outside / geometry.POINTS_PER_INCH:.3f} in from "
                    "the outside edge"
                )
            if top + tol < geometry.OUTER_MIN or page.height - bottom + tol < geometry.OUTER_MIN:
                problems.append(
                    f"page {index + 1}: text closer than 0.25 in to the top or bottom edge"
                )
        return problems, texts, folios
