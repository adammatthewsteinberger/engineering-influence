"""Renders every page of a PDF to a numbered PNG with pdftoppm or mutool."""

import shutil
import subprocess  # nosec B404
from pathlib import Path

from engineering_influence.publishing.qa.page_file_number import PageFileNumber
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError


class PageRasterizer:
    """Uses poppler's pdftoppm when present, otherwise MuPDF's mutool."""

    def command(self) -> str:
        """The renderer found on PATH."""
        if shutil.which("pdftoppm"):
            return "pdftoppm"
        if shutil.which("mutool"):
            return "mutool"
        raise BookBuildError("visual QA needs pdftoppm (poppler-utils) or mutool on PATH")

    def clear_pages(self, directory: Path) -> None:
        """Remove only generated page images in the named QA directory."""
        if not directory.exists():
            return
        for path in (*directory.glob("page-*.png"), *directory.glob("render-*.png")):
            path.unlink()

    def rasterize(self, pdf: Path, pages_dir: Path, dpi: int, page_count: int) -> None:
        """Write page-0001.png ... into pages_dir; the pdf path must be absolute."""
        pages_dir.mkdir(parents=True, exist_ok=True)
        self.clear_pages(pages_dir)
        if self.command() == "pdftoppm":
            cmd = [
                "pdftoppm",
                "-r",
                str(dpi),
                "-png",
                "-f",
                "1",
                "-l",
                str(page_count),
                str(pdf),
                str(pages_dir / "render"),
            ]
        else:
            cmd = [
                "mutool",
                "draw",
                "-r",
                str(dpi),
                "-F",
                "png",
                "-o",
                str(pages_dir / "render-%04d.png"),
                str(pdf),
            ]
        # Fixed argument list, no shell; the PDF path is absolute so it cannot read as an option.
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603
        if proc.returncode:
            detail = (proc.stderr or proc.stdout)[-4000:]
            raise BookBuildError(f"PDF renderer failed:\n{detail}")
        numbers = PageFileNumber()
        rendered = sorted(pages_dir.glob("render-*.png"), key=numbers.of)
        if len(rendered) != page_count:
            raise BookBuildError(f"renderer produced {len(rendered)} pages; PDF has {page_count}")
        for index, path in enumerate(rendered, start=1):
            path.rename(pages_dir / f"page-{index:04d}.png")
