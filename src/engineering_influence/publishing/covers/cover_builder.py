"""Builds every cover file for one book: ebook, print panels, and both wraps."""

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from PIL import Image

from engineering_influence.publishing.covers.builtin_cover_style import BuiltinCoverStyle
from engineering_influence.publishing.covers.cover_files import CoverFiles
from engineering_influence.publishing.covers.cover_renderer import CoverRenderer
from engineering_influence.publishing.covers.cover_style import CoverStyle
from engineering_influence.publishing.covers.ebook_border import EbookBorder
from engineering_influence.publishing.covers.ebook_cover_verifier import EbookCoverVerifier
from engineering_influence.publishing.covers.font_loader import FontLoader
from engineering_influence.publishing.covers.gradient_painter import GradientPainter
from engineering_influence.publishing.covers.image_verifier import ImageVerifier
from engineering_influence.publishing.covers.interior_page_count import InteriorPageCount
from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec as Kdp
from engineering_influence.publishing.covers.layout_factory import LayoutFactory
from engineering_influence.publishing.covers.painter_registry import PainterRegistry
from engineering_influence.publishing.covers.print_pdf_verifier import PrintPdfVerifier
from engineering_influence.publishing.package_assets import PackageAssets
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError
from engineering_influence.publishing.typesetting.book_builder import BookBuilder


class CoverBuilder:
    """Reads books/<slug>.toml and output/<slug>.pdf; writes output/covers/<slug>/.

    The files, each verified against KDP's rules before the build succeeds:
    ebook JPEG and TIFF, front and back panels, and the paperback and hardcover wraps as
    TIFF and as the single-page PDF KDP requires.
    """

    def __init__(
        self,
        layout: ProjectLayout,
        registry: PainterRegistry | None = None,
        styles: Mapping[str, CoverStyle] | None = None,
        font_dirs: list[Path] | None = None,
    ) -> None:
        self._layout = layout
        self._registry = registry or PainterRegistry()
        if registry is None:
            self._registry.register("gradient", GradientPainter())
        self._styles = dict(styles or {})
        self._font_dirs = font_dirs if font_dirs is not None else [layout.root / "covers" / "fonts"]

    def build(self, slug: str, preview: bool = False, hardcover_pdf: Path | None = None) -> Path:
        """Return the directory the covers were written to."""
        if not BookBuilder.SLUG.fullmatch(slug):
            raise BookBuildError(f"invalid book slug: {slug!r}")
        config = self._layout.books / f"{slug}.toml"
        if not config.exists():
            raise BookBuildError(f"no such book config: {config}")
        meta = tomllib.loads(config.read_text(encoding="utf-8"))
        style = self._styles.get(slug) or BuiltinCoverStyle().for_book(meta)
        with PackageAssets().directory() as assets:
            fonts = FontLoader([*self._font_dirs, assets / "fonts"])
            return self._build(slug, meta, style, fonts, preview, hardcover_pdf)

    def _build(
        self,
        slug: str,
        meta: dict[str, Any],
        st: CoverStyle,
        fonts: FontLoader,
        preview: bool,
        hardcover_pdf: Path | None,
    ) -> Path:
        counter = InteriorPageCount()
        pages = counter.of(self._layout.output / f"{slug}.pdf")
        if hardcover_pdf and not hardcover_pdf.is_absolute():
            hardcover_pdf = self._layout.root / hardcover_pdf
        hardcover_pages = counter.of(hardcover_pdf) if hardcover_pdf else pages
        formats = meta.get("formats", {})
        limit = int(formats.get("hardcover_max_pages", 550)) if isinstance(formats, dict) else 550
        if hardcover_pdf and hardcover_pages > limit:
            raise BookBuildError(
                f"[{slug}] hardcover interior has {hardcover_pages} pages; "
                f"configured maximum is {limit}"
            )
        out = self._layout.output / "covers" / slug
        out.mkdir(parents=True, exist_ok=True)
        title, author = str(meta["title"]), str(meta["author"])
        render = CoverRenderer(self._registry, fonts).render
        files, factory, border = CoverFiles(), LayoutFactory(), EbookBorder()

        img = render(factory.ebook(), st, meta)
        if border.is_light_edge(img):
            img = border.add(img)
        (out / f"{slug}-ebook.jpg").write_bytes(files.jpeg_bytes(img))
        files.save_tiff(img, out / f"{slug}-ebook.tif", compress=False)
        if preview:
            img.resize((400, 640), Image.Resampling.LANCZOS).save(
                out / f"{slug}-ebook-preview.jpg", quality=88
            )

        pb = factory.paperback(pages)
        wrap = render(pb, st, meta)
        files.save_tiff(wrap, out / f"{slug}-paperback-wrap.tif")
        files.write_pdf(
            wrap,
            out / f"{slug}-paperback-wrap.pdf",
            pb.width,
            pb.height,
            f"{title}: paperback cover",
            author,
        )

        def px(v: float) -> int:
            return round(v * Kdp.PPI)

        front = wrap.crop((px(pb.front.x0 - Kdp.BLEED), 0, wrap.size[0], wrap.size[1]))
        back = wrap.crop((0, 0, px(Kdp.BLEED + Kdp.TRIM_W + Kdp.BLEED), wrap.size[1]))
        files.save_tiff(front, out / f"{slug}-front.tif")
        files.save_tiff(back, out / f"{slug}-back.tif")

        hc = factory.hardcover(hardcover_pages)
        hwrap = render(hc, st, meta)
        files.save_tiff(hwrap, out / f"{slug}-hardcover-wrap.tif")
        files.write_pdf(
            hwrap,
            out / f"{slug}-hardcover-wrap.pdf",
            hc.width,
            hc.height,
            f"{title}: hardcover cover",
            author,
        )
        if preview:
            hwrap.resize((hwrap.size[0] // 6, hwrap.size[1] // 6), Image.Resampling.LANCZOS).save(
                out / f"{slug}-hardcover-preview.jpg", quality=88
            )

        panel_w = Kdp.TRIM_W + 2 * Kdp.BLEED
        images, ebooks, pdfs = ImageVerifier(), EbookCoverVerifier(), PrintPdfVerifier()
        problems = (
            ebooks.run(out / f"{slug}-ebook.jpg")
            + ebooks.run(out / f"{slug}-ebook.tif")
            + images.run(out / f"{slug}-front.tif", panel_w, pb.height, Kdp.PPI)
            + images.run(out / f"{slug}-back.tif", panel_w, pb.height, Kdp.PPI)
            + images.run(out / f"{slug}-paperback-wrap.tif", pb.width, pb.height, Kdp.PPI)
            + images.run(out / f"{slug}-hardcover-wrap.tif", hc.width, hc.height, Kdp.PPI)
            + pdfs.run(out / f"{slug}-paperback-wrap.pdf", pb.width, pb.height)
            + pdfs.run(out / f"{slug}-hardcover-wrap.pdf", hc.width, hc.height)
        )
        if problems:
            raise BookBuildError(f"[{slug}] cover check failed: " + "; ".join(problems))
        return out
