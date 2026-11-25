# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""PDF facts read with pypdf (structure) and pdfplumber (text and layout)."""

from pathlib import Path
from typing import Any

from engineering_influence.interfaces.pdf_inspector_interface import PdfInspectorInterface
from engineering_influence.models.publishing.pdf_document import PdfDocument
from engineering_influence.models.publishing.pdf_page import PdfPage
from engineering_influence.models.publishing.pdf_word import PdfWord


class PypdfPdfInspector(PdfInspectorInterface):
    """Reads a finished PDF so nothing is taken on trust.

    The libraries are imported when a file is read, so the rest of ``ei`` works in an install
    without the ``publishing`` extra.
    """

    def inspect(self, path: Path) -> PdfDocument:
        """Read every page of the PDF."""
        import pdfplumber
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        with pdfplumber.open(str(path)) as pdf:
            pages = tuple(
                self._page(structure, layout)
                for structure, layout in zip(reader.pages, pdf.pages, strict=True)
            )
        return PdfDocument(pages, bool(reader.outline))

    def page_count(self, path: Path) -> int | None:
        """The number of pages, or None when the file does not exist."""
        from pypdf import PdfReader

        if not path.exists():
            return None
        return len(PdfReader(str(path)).pages)

    def _page(self, structure: Any, layout: Any) -> PdfPage:
        chars = layout.chars
        text_box = (
            (
                min(c["x0"] for c in chars),
                max(c["x1"] for c in chars),
                min(c["top"] for c in chars),
                max(c["bottom"] for c in chars),
            )
            if chars
            else None
        )
        words = tuple(
            PdfWord(str(word["text"]), word["top"], word["bottom"])
            for word in layout.extract_words(use_text_flow=False, keep_blank_chars=False)
        )
        return PdfPage(
            width=layout.width,
            height=layout.height,
            media_width=float(structure.mediabox.width),
            media_height=float(structure.mediabox.height),
            text=layout.extract_text(x_tolerance=1.5) or "",
            words=words,
            text_box=text_box,
            has_annotations="/Annots" in structure,
            has_group="/Group" in structure,
            unembedded_fonts=frozenset(self._unembedded_fonts(structure)),
        )

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
