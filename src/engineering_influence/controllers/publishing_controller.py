# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Transport-neutral publishing controller: audit, build, and publish a project's books."""

from pathlib import Path
from typing import Any

from engineering_influence.publishing.audit_report_text import AuditReportText
from engineering_influence.publishing.book_auditor import BookAuditor
from engineering_influence.publishing.covers.cover_builder import CoverBuilder
from engineering_influence.publishing.covers.cover_plugin_loader import CoverPluginLoader
from engineering_influence.publishing.covers.cover_style import CoverStyle
from engineering_influence.publishing.covers.gradient_painter import GradientPainter
from engineering_influence.publishing.covers.painter_registry import PainterRegistry
from engineering_influence.publishing.epub.epub_builder import EpubBuilder
from engineering_influence.publishing.epub.epub_verifier import EpubVerifier
from engineering_influence.publishing.epub.tex4ebook_compiler import Tex4ebookCompiler
from engineering_influence.publishing.pdf_verifier import PdfVerifier
from engineering_influence.publishing.project_config import ProjectConfig
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.qa.render_qa import RenderQa
from engineering_influence.publishing.release.publish_pipeline import PublishPipeline
from engineering_influence.publishing.release.publish_steps import PublishSteps
from engineering_influence.publishing.release_auditor import ReleaseAuditor
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError
from engineering_influence.publishing.typesetting.book_builder import BookBuilder
from engineering_influence.publishing.typesetting.book_loader import BookLoader
from engineering_influence.publishing.typesetting.latex_compiler import LatexCompiler


class PublishingController:
    """One entry point per publishing operation, shared by every transport.

    The controller owns the wiring a transport should not repeat: the project's layout, its
    cover plugin, and the builders. Operations return text for a person or plain dictionaries
    for a machine, and raise BookBuildError (or ManuscriptError) when something is wrong.
    """

    def __init__(
        self,
        config: ProjectConfig,
        latex: LatexCompiler | None = None,
        tex4ebook: Tex4ebookCompiler | None = None,
        qa: RenderQa | None = None,
    ) -> None:
        self._config = config
        self._layout = config.layout()
        self._latex = latex
        self._tex4ebook = tex4ebook
        self._qa = qa or RenderQa(config.root)

    @property
    def layout(self) -> ProjectLayout:
        """The project's directory layout."""
        return self._layout

    def audit(self, slug: str, *, strict_release: bool = False) -> tuple[dict[str, Any], bool, str]:
        """Return (both reports as dictionaries, whether the manuscript passes, text)."""
        config = self._book_config(slug)
        manuscript = BookAuditor(self._config.root).audit(config)
        release = ReleaseAuditor(self._config.root).audit(config, strict=strict_release)
        text = AuditReportText()
        summary = f"{text.manuscript(manuscript)}\n{text.release(release)}"
        ok = not manuscript.issues and not release.errors
        return {"manuscript": manuscript.as_dict(), "release": release.as_dict()}, ok, summary

    def build(
        self, slug: str, *, hardcover: bool = False, tex_only: bool = False, verify: bool = True
    ) -> str:
        """Build the interior PDF (or only its LaTeX) and verify the PDF."""
        path = BookBuilder(self._layout, compiler=self._latex).build(
            slug, tex_only=tex_only, hardcover=hardcover
        )
        if tex_only or not verify:
            return f"[{slug}] wrote {self._relative(path)}"
        log_slug = f"{slug}-hardcover" if hardcover else slug
        log = self._layout.build / log_slug / f"{slug}.log"
        problems = PdfVerifier().verify(path, self._layout.books / f"{slug}.toml", log)
        self._raise_on(slug, problems)
        return f"[{slug}] built {self._relative(path)}\n[{slug}] all checks passed"

    def epub(self, slug: str, *, tex_only: bool = False, verify: bool = True) -> str:
        """Build the EPUB (or only its LaTeX) and verify the EPUB."""
        path = EpubBuilder(self._layout, compiler=self._tex4ebook).build(slug, tex_only=tex_only)
        if tex_only or not verify:
            return f"[{slug}] wrote {self._relative(path)}"
        book = BookLoader(self._config.root).load(self._layout.books / f"{slug}.toml")
        self._raise_on(slug, EpubVerifier().verify(path, book))
        return f"[{slug}] built {self._relative(path)}\n[{slug}] all checks passed"

    def covers(self, slug: str, *, preview: bool = False, hardcover_pdf: Path | None = None) -> str:
        """Build and verify every cover file."""
        out = self._cover_builder().build(slug, preview=preview, hardcover_pdf=hardcover_pdf)
        return f"[{slug}] covers written to {self._relative(out)}\n[{slug}] all cover checks passed"

    def qa(
        self, pdf: Path, *, output: Path | None = None, dpi: int = 90
    ) -> tuple[dict[str, Any], bool]:
        """Render every page of a PDF; return (the report, whether no blank run is overlong)."""
        pdf = pdf if pdf.is_absolute() else self._config.root / pdf
        if not pdf.exists():
            raise BookBuildError(f"PDF not found: {pdf}")
        target = output or self._layout.build / pdf.stem / "visual-qa"
        report = self._qa.render(pdf, target, dpi=dpi)
        return report.as_dict(), not report.unexpected_blank_pages

    def publish(
        self,
        slug: str,
        *,
        dpi: int = 90,
        audit_only: bool = False,
        no_render: bool = False,
        report_path: Path | None = None,
        strict_release: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        """Run the complete acceptance pipeline for one book."""
        steps = PublishSteps(
            self._layout,
            BookBuilder(self._layout, compiler=self._latex),
            self._cover_builder(),
            EpubBuilder(self._layout, compiler=self._tex4ebook),
        )
        pipeline = PublishPipeline(self._layout, steps, qa=self._qa)
        return pipeline.publish(
            slug,
            dpi=dpi,
            audit_only=audit_only,
            no_render=no_render,
            report_path=report_path,
            strict_release=strict_release,
        )

    def book_slugs(self) -> list[str]:
        """Every book the project configures."""
        return sorted(path.stem for path in self._layout.books.glob("*.toml"))

    def _cover_builder(self) -> CoverBuilder:
        registry = PainterRegistry()
        registry.register("gradient", GradientPainter())
        loader = CoverPluginLoader()
        self._config.activate()
        styles: dict[str, CoverStyle] = loader.load(registry, self._config.root)
        if self._config.cover_plugin:
            styles.update(
                loader.load_reference(self._config.cover_plugin, registry, self._config.root)
            )
        return CoverBuilder(
            self._layout, registry=registry, styles=styles, font_dirs=self._config.font_dirs()
        )

    def _book_config(self, slug: str) -> Path:
        path = self._layout.books / f"{slug}.toml"
        if not path.exists():
            raise BookBuildError(f"no such book config: {self._relative(path)}")
        return path

    def _relative(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self._config.root))
        except ValueError:
            return str(path.resolve())

    def _raise_on(self, slug: str, problems: list[str]) -> None:
        if problems:
            raise BookBuildError("\n".join(f"[{slug}] FAIL {problem}" for problem in problems))
