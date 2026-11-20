# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Transport-neutral publishing controller: audit, build, and publish a project's books."""

from pathlib import Path
from typing import Any

from engineering_influence.controllers.interfaces.publishing_controller_interface import (
    PublishingControllerInterface,
)
from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.interfaces.book_loader_interface import BookLoaderInterface
from engineering_influence.interfaces.cover_builder_interface import CoverBuilderInterface
from engineering_influence.interfaces.cover_builder_provider_interface import (
    CoverBuilderProviderInterface,
)
from engineering_influence.interfaces.manuscript_source_interface import ManuscriptSourceInterface
from engineering_influence.interfaces.pdf_inspector_interface import PdfInspectorInterface
from engineering_influence.interfaces.publish_pipeline_provider_interface import (
    PublishPipelineProviderInterface,
)
from engineering_influence.interfaces.render_qa_interface import RenderQaInterface
from engineering_influence.models.publishing.project_config import ProjectConfig
from engineering_influence.models.publishing.project_layout import ProjectLayout
from engineering_influence.services.epub.epub_builder import EpubBuilder
from engineering_influence.services.epub.epub_verifier import EpubVerifier
from engineering_influence.services.publishing.audit_report_text import AuditReportText
from engineering_influence.services.publishing.book_auditor import BookAuditor
from engineering_influence.services.publishing.interfaces.pdf_verifier_interface import (
    PdfVerifierInterface,
)
from engineering_influence.services.publishing.release_auditor import ReleaseAuditor
from engineering_influence.services.typesetting.interfaces.book_builder_interface import (
    BookBuilderInterface,
)


class PublishingController(PublishingControllerInterface):
    """One entry point per publishing operation, shared by every transport.

    The controller owns the wiring a transport should not repeat: the project's layout, its
    cover plugin, and the builders. Operations return text for a person or plain dictionaries
    for a machine, and raise BookBuildError (or ManuscriptError) when something is wrong.
    """

    def __init__(
        self,
        config: ProjectConfig,
        files: ManuscriptSourceInterface,
        pdfs: PdfInspectorInterface,
        loader: BookLoaderInterface,
        builder: BookBuilderInterface,
        pdf_verifier: PdfVerifierInterface,
        epub: EpubBuilder,
        epub_verifier: EpubVerifier,
        covers: CoverBuilderProviderInterface,
        qa: RenderQaInterface,
        publisher: PublishPipelineProviderInterface,
    ) -> None:
        self._config = config
        self._files = files
        self._pdfs = pdfs
        self._loader = loader
        self._layout = config.layout()
        self._builder = builder
        self._pdf_verifier = pdf_verifier
        self._epub = epub
        self._epub_verifier = epub_verifier
        self._covers = covers
        self._qa = qa
        self._publisher = publisher

    @property
    def layout(self) -> ProjectLayout:
        """The project's directory layout."""
        return self._layout

    def audit(self, slug: str, *, strict_release: bool = False) -> tuple[dict[str, Any], bool, str]:
        """Return (both reports as dictionaries, whether the manuscript passes, text)."""
        config = self._book_config(slug)
        manuscript = BookAuditor(self._config.root, self._files).audit(config)
        release = ReleaseAuditor(self._config.root, self._files, self._pdfs).audit(
            config, strict=strict_release
        )
        text = AuditReportText()
        summary = f"{text.manuscript(manuscript)}\n{text.release(release)}"
        ok = not manuscript.issues and not release.errors
        return {"manuscript": manuscript.as_dict(), "release": release.as_dict()}, ok, summary

    def build(
        self, slug: str, *, hardcover: bool = False, tex_only: bool = False, verify: bool = True
    ) -> str:
        """Build the interior PDF (or only its LaTeX) and verify the PDF."""
        path = self._builder.build(slug, tex_only=tex_only, hardcover=hardcover)
        if tex_only or not verify:
            return f"[{slug}] wrote {self._relative(path)}"
        log_slug = f"{slug}-hardcover" if hardcover else slug
        log = self._layout.build / log_slug / f"{slug}.log"
        problems = self._pdf_verifier.verify(path, self._layout.books / f"{slug}.toml", log)
        self._raise_on(slug, problems)
        return f"[{slug}] built {self._relative(path)}\n[{slug}] all checks passed"

    def epub(self, slug: str, *, tex_only: bool = False, verify: bool = True) -> str:
        """Build the EPUB (or only its LaTeX) and verify the EPUB."""
        path = self._epub.build(slug, tex_only=tex_only)
        if tex_only or not verify:
            return f"[{slug}] wrote {self._relative(path)}"
        book = self._loader.load(self._layout.books / f"{slug}.toml")
        self._raise_on(slug, self._epub_verifier.verify(path, book))
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
        pipeline = self._publisher.provide()
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

    def _cover_builder(self) -> CoverBuilderInterface:
        return self._covers.provide()

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
