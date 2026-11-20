# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Builds one ebook: Markdown to LaTeX to EPUB."""

from pathlib import Path

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.interfaces.book_loader_interface import BookLoaderInterface
from engineering_influence.interfaces.build_workspace_interface import BuildWorkspaceInterface
from engineering_influence.interfaces.epub_compiler_interface import EpubCompilerInterface
from engineering_influence.interfaces.manuscript_source_interface import ManuscriptSourceInterface
from engineering_influence.interfaces.package_assets_interface import PackageAssetsInterface
from engineering_influence.models.publishing.project_layout import ProjectLayout
from engineering_influence.services.epub.epub_identifier import EpubIdentifier
from engineering_influence.services.epub.epub_repacker import EpubRepacker
from engineering_influence.services.epub.interfaces.epub_builder_interface import (
    EpubBuilderInterface,
)
from engineering_influence.services.typesetting.book_builder import BookBuilder
from engineering_influence.services.typesetting.ebook_document import EbookDocument


class EpubBuilder(EpubBuilderInterface):
    """The ebook shares one Markdown to LaTeX conversion with the print interior.

    The ebook embeds no fonts (readers supply their own, and KDP charges per megabyte of
    delivery), but it does embed its cover, which must exist already.
    """

    def __init__(
        self,
        layout: ProjectLayout,
        loader: BookLoaderInterface,
        compiler: EpubCompilerInterface,
        workspace: BuildWorkspaceInterface,
        assets: PackageAssetsInterface,
        repacker: EpubRepacker,
        files: ManuscriptSourceInterface,
        identifier: EpubIdentifier,
    ) -> None:
        self._layout = layout
        self._loader = loader
        self._compiler = compiler
        self._workspace = workspace
        self._assets = assets
        self._repacker = repacker
        self._files = files
        self._identifier = identifier

    def build(self, slug: str, *, tex_only: bool = False) -> Path:
        """Return the ebook .tex path when tex_only, otherwise the finished EPUB path."""
        if not BookBuilder.SLUG.fullmatch(slug):
            raise BookBuildError(f"invalid book slug: {slug!r}")
        config = self._layout.books / f"{slug}.toml"
        if not self._files.exists(config):
            raise BookBuildError(f"no such book config: {config}")
        with self._assets.directory() as assets:
            return self._build(config, slug, assets, tex_only)

    def _build(self, config: Path, slug: str, assets: Path, tex_only: bool) -> Path:
        book = self._loader.load(config)
        workdir = self._layout.build / slug / "epub"
        self._workspace.prepare_ebook(workdir, assets)
        self._workspace.write_text(workdir / "ebook-meta.tex", self._identifier.meta_tex(book))
        tex_path = workdir / f"{slug}.tex"
        self._workspace.write_text(tex_path, EbookDocument().render(book))
        if tex_only:
            return tex_path
        status, output = self._compiler.compile(workdir, f"{slug}.tex")
        epub = workdir / f"{slug}.epub"
        if status != 0 or not self._files.exists(epub):
            log = workdir / f"{slug}.log"
            if self._files.exists(log):
                tail = self._files.read_text(log, errors="replace")[-4000:]
            else:
                tail = output[-4000:]
            raise BookBuildError(f"[{slug}] tex4ebook failed:\n{tail}")
        self._workspace.ensure_directory(self._layout.output)
        out = self._layout.output / f"{slug}.epub"
        self._repacker.repack(epub, book, out)
        return out
