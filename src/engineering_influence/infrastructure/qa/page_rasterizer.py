# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Renders every page of a PDF to a numbered PNG with pdftoppm or mutool."""

import shutil
from pathlib import Path

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.process.interfaces.process_runner_interface import (
    ProcessRunnerInterface,
)
from engineering_influence.infrastructure.process.process_runner import ProcessRunner
from engineering_influence.infrastructure.qa.interfaces.page_rasterizer_interface import (
    PageRasterizerInterface,
)
from engineering_influence.models.qa.page_file_number import PageFileNumber
from engineering_influence.models.tool_limits import ToolLimits


class PageRasterizer(PageRasterizerInterface):
    """Uses poppler's pdftoppm when present, otherwise MuPDF's mutool.

    A renderer that passes its time, memory or disk limit is stopped, with a BookBuildError.
    The disk limit applies to the page directory.
    """

    DEFAULT_LIMITS = ToolLimits(
        timeout_seconds=600.0, max_memory_bytes=2 * 2**30, max_disk_bytes=4 * 2**30
    )

    def __init__(
        self, runner: ProcessRunnerInterface | None = None, limits: ToolLimits | None = None
    ) -> None:
        """Remember the process runner and limits the rasterizer runs under."""
        self._runner = runner or ProcessRunner()
        self._limits = limits or self.DEFAULT_LIMITS

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
        status, stdout, stderr = self._runner.run(cmd, self._limits, watch=pages_dir)
        if status:
            detail = (stderr or stdout)[-4000:]
            raise BookBuildError(f"PDF renderer failed:\n{detail}")
        numbers = PageFileNumber()
        rendered = sorted(pages_dir.glob("render-*.png"), key=numbers.of)
        if len(rendered) != page_count:
            raise BookBuildError(f"renderer produced {len(rendered)} pages; PDF has {page_count}")
        for index, path in enumerate(rendered, start=1):
            path.rename(pages_dir / f"page-{index:04d}.png")
