"""Renders every PDF page and produces a repeatable visual-QA evidence set."""

from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from engineering_influence.publishing.path_relativizer import PathRelativizer
from engineering_influence.publishing.qa.blank_page_detector import BlankPageDetector
from engineering_influence.publishing.qa.contact_sheet_builder import ContactSheetBuilder
from engineering_influence.publishing.qa.page_file_number import PageFileNumber
from engineering_influence.publishing.qa.page_rasterizer import PageRasterizer
from engineering_influence.publishing.qa.page_record import PageRecord
from engineering_influence.publishing.qa.render_report import RenderReport


class RenderQa:
    """Replaces the manual part of visual review: rendering every page, keeping page numbers
    aligned with images, and assembling a reviewable set. It does not replace a human reading
    the contact sheets."""

    def __init__(self, root: Path, rasterizer: PageRasterizer | None = None) -> None:
        self._relativizer = PathRelativizer(root)
        self._rasterizer = rasterizer or PageRasterizer()

    def render(self, pdf: Path, output: Path, *, dpi: int = 90) -> RenderReport:
        """Render the PDF into output/pages and output/contact-NNN.png."""
        pdf, output = pdf.resolve(), output.resolve()
        page_count = len(PdfReader(str(pdf)).pages)
        pages_dir = output / "pages"
        output.mkdir(parents=True, exist_ok=True)
        self._rasterizer.rasterize(pdf, pages_dir, dpi, page_count)
        page_paths = sorted(pages_dir.glob("page-*.png"), key=PageFileNumber().of)
        detector = BlankPageDetector()
        pages: list[PageRecord] = []
        for index, path in enumerate(page_paths, start=1):
            with Image.open(path) as image:
                width, height = image.size
                blank = detector.is_blank(image)
            pages.append(
                PageRecord(
                    index,
                    self._relativizer.relative(path),
                    width,
                    height,
                    path.stat().st_size,
                    blank,
                )
            )
        sheets = ContactSheetBuilder(self._relativizer)
        sheets.clear(output)
        return RenderReport(
            1,
            self._relativizer.relative(pdf),
            self._relativizer.relative(output),
            dpi,
            page_count,
            len(page_paths),
            sheets.build(page_paths, output),
            pages,
        )
