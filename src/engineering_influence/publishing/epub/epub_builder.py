"""Builds one ebook: Markdown to LaTeX to EPUB."""

import shutil
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

from engineering_influence.publishing.epub.cover_image import CoverImage
from engineering_influence.publishing.epub.epub_identifier import EpubIdentifier
from engineering_influence.publishing.epub.epub_repacker import EpubRepacker
from engineering_influence.publishing.epub.tex4ebook_compiler import Tex4ebookCompiler
from engineering_influence.publishing.package_assets import PackageAssets
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError
from engineering_influence.publishing.typesetting.book_builder import BookBuilder
from engineering_influence.publishing.typesetting.book_loader import BookLoader
from engineering_influence.publishing.typesetting.ebook_document import EbookDocument


class EpubBuilder:
    """The ebook shares one Markdown to LaTeX conversion with the print interior.

    The ebook embeds no fonts (readers supply their own, and KDP charges per megabyte of
    delivery), but it does embed its cover, which must exist already.
    """

    def __init__(
        self,
        layout: ProjectLayout,
        assets: Path | None = None,
        compiler: Tex4ebookCompiler | None = None,
        strict: bool = True,
        identifier: EpubIdentifier | None = None,
    ) -> None:
        self._layout = layout
        self._assets = assets
        self._compiler = compiler or Tex4ebookCompiler()
        self._loader = BookLoader(layout.root, strict)
        self._identifier = identifier or EpubIdentifier()
        self._repacker = EpubRepacker(CoverImage(layout), self._identifier)

    def build(self, slug: str, *, tex_only: bool = False) -> Path:
        """Return the ebook .tex path when tex_only, otherwise the finished EPUB path."""
        if not BookBuilder.SLUG.fullmatch(slug):
            raise BookBuildError(f"invalid book slug: {slug!r}")
        config = self._layout.books / f"{slug}.toml"
        if not config.exists():
            raise BookBuildError(f"no such book config: {config}")
        context: AbstractContextManager[Path] = (
            nullcontext(self._assets) if self._assets else PackageAssets().directory()
        )
        with context as assets:
            return self._build(config, slug, assets, tex_only)

    def _build(self, config: Path, slug: str, assets: Path, tex_only: bool) -> Path:
        book = self._loader.load(config)
        workdir = self._layout.build / slug / "epub"
        if workdir.exists():
            shutil.rmtree(workdir)
        workdir.mkdir(parents=True)
        for name in ("fine-ebook.sty", "fine-ebook.cfg", "fine-ebook.css"):
            shutil.copy(assets / name, workdir / name)
        (workdir / "ebook-meta.tex").write_text(self._identifier.meta_tex(book), encoding="utf-8")
        tex_path = workdir / f"{slug}.tex"
        tex_path.write_text(EbookDocument().render(book), encoding="utf-8")
        if tex_only:
            return tex_path
        status, output = self._compiler.compile(workdir, f"{slug}.tex")
        epub = workdir / f"{slug}.epub"
        if status != 0 or not epub.exists():
            log = workdir / f"{slug}.log"
            tail = log.read_text(errors="replace")[-4000:] if log.exists() else output[-4000:]
            raise BookBuildError(f"[{slug}] tex4ebook failed:\n{tail}")
        self._layout.output.mkdir(exist_ok=True)
        out = self._layout.output / f"{slug}.epub"
        self._repacker.repack(epub, book, out)
        return out
