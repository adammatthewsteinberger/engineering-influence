"""Builds one book: Markdown manuscripts to LaTeX to PDF."""

import datetime as dt
import re
import shutil
from pathlib import Path

from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError
from engineering_influence.publishing.typesetting.book_loader import BookLoader
from engineering_influence.publishing.typesetting.latex_compiler import LatexCompiler
from engineering_influence.publishing.typesetting.print_document import PrintDocument


class BookBuilder:
    """Writes the .tex source, compiles it, and copies the PDF to the output directory."""

    SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")

    def __init__(
        self,
        layout: ProjectLayout,
        assets: Path,
        compiler: LatexCompiler | None = None,
        strict: bool = True,
    ) -> None:
        self._layout = layout
        self._assets = assets
        self._compiler = compiler or LatexCompiler()
        self._loader = BookLoader(layout.root, strict)

    def build(self, slug: str, *, tex_only: bool = False, hardcover: bool = False) -> Path:
        """Return the .tex path when tex_only, otherwise the finished PDF path."""
        if not self.SLUG.fullmatch(slug):
            raise BookBuildError(f"invalid book slug: {slug!r}")
        config = self._layout.books / f"{slug}.toml"
        if not config.exists():
            raise BookBuildError(f"no such book config: {config}")
        book = self._loader.load(config)
        build_slug = f"{slug}-hardcover" if hardcover else slug
        workdir = self._layout.build / build_slug
        workdir.mkdir(parents=True, exist_ok=True)
        if hardcover:
            shutil.copy(
                self._assets / "fine-book-hardcover.cls", workdir / "fine-book-hardcover.cls"
            )
        shutil.copy(self._assets / "fine-book.cls", workdir / "fine-book.cls")
        # The interior fonts travel with the package, so the PDF does not depend on which TeX
        # distribution built it.
        shutil.copytree(self._assets / "fonts", workdir / "fonts", dirs_exist_ok=True)
        tex_path = workdir / f"{slug}.tex"
        tex_path.write_text(PrintDocument().render(book, hardcover=hardcover), encoding="utf-8")
        if tex_only:
            return tex_path
        year = int(book.meta.get("year", 2026))
        epoch = int(dt.datetime(year, 1, 1, tzinfo=dt.UTC).timestamp())
        status, stdout = self._compiler.compile(workdir, f"{slug}.tex", epoch)
        if status != 0:
            log = workdir / f"{slug}.log"
            tail = log.read_text(errors="replace")[-4000:] if log.exists() else stdout[-4000:]
            raise BookBuildError(f"[{slug}] LaTeX failed:\n{tail}")
        self._layout.output.mkdir(exist_ok=True)
        pdf = self._layout.output / f"{build_slug}.pdf"
        shutil.copy(workdir / f"{slug}.pdf", pdf)
        return pdf
