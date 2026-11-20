# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Builds one book: Markdown manuscripts to LaTeX to PDF."""

import datetime as dt
from pathlib import Path

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.interfaces.book_loader_interface import BookLoaderInterface
from engineering_influence.interfaces.build_workspace_interface import BuildWorkspaceInterface
from engineering_influence.interfaces.latex_compiler_interface import LatexCompilerInterface
from engineering_influence.interfaces.manuscript_source_interface import ManuscriptSourceInterface
from engineering_influence.interfaces.package_assets_interface import PackageAssetsInterface
from engineering_influence.models.publishing.project_layout import ProjectLayout
from engineering_influence.models.typesetting.book_slug import BookSlug
from engineering_influence.services.typesetting.interfaces.book_builder_interface import (
    BookBuilderInterface,
)
from engineering_influence.services.typesetting.print_document import PrintDocument


class BookBuilder(BookBuilderInterface):
    """Writes the .tex source, compiles it, and copies the PDF to the output directory."""

    SLUG = BookSlug.PATTERN

    def __init__(
        self,
        layout: ProjectLayout,
        loader: BookLoaderInterface,
        compiler: LatexCompilerInterface,
        workspace: BuildWorkspaceInterface,
        assets: PackageAssetsInterface,
        files: ManuscriptSourceInterface,
    ) -> None:
        self._layout = layout
        self._loader = loader
        self._compiler = compiler
        self._workspace = workspace
        self._assets = assets
        self._files = files

    def build(self, slug: str, *, tex_only: bool = False, hardcover: bool = False) -> Path:
        """Return the .tex path when tex_only, otherwise the finished PDF path.

        Class files and fonts come from the assets provider: the ones bundled in the package,
        or a directory of the project's own.
        """
        if not self.SLUG.fullmatch(slug):
            raise BookBuildError(f"invalid book slug: {slug!r}")
        config = self._layout.books / f"{slug}.toml"
        if not self._files.exists(config):
            raise BookBuildError(f"no such book config: {config}")
        with self._assets.directory() as assets:
            return self._build(config, slug, assets, tex_only, hardcover)

    def _build(
        self, config: Path, slug: str, assets: Path, tex_only: bool, hardcover: bool
    ) -> Path:
        book = self._loader.load(config)
        build_slug = f"{slug}-hardcover" if hardcover else slug
        workdir = self._layout.build / build_slug
        self._workspace.prepare(workdir, assets, hardcover)
        tex_path = workdir / f"{slug}.tex"
        self._workspace.write_text(tex_path, PrintDocument().render(book, hardcover=hardcover))
        if tex_only:
            return tex_path
        year = int(book.meta.get("year", 2026))
        epoch = int(dt.datetime(year, 1, 1, tzinfo=dt.UTC).timestamp())
        status, stdout = self._compiler.compile(workdir, f"{slug}.tex", epoch)
        if status != 0:
            log = workdir / f"{slug}.log"
            tail = (
                self._files.read_text(log, errors="replace")[-4000:]
                if self._files.exists(log)
                else stdout[-4000:]
            )
            raise BookBuildError(f"[{slug}] LaTeX failed:\n{tail}")
        pdf = self._layout.output / f"{build_slug}.pdf"
        self._workspace.deliver(workdir / f"{slug}.pdf", pdf)
        return pdf
