# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The build actions of a publication: interior PDFs, covers, and the EPUB, each verified."""

from collections.abc import Callable
from pathlib import Path

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.interfaces.book_loader_interface import BookLoaderInterface
from engineering_influence.interfaces.cover_builder_interface import CoverBuilderInterface
from engineering_influence.interfaces.epub_verifier_interface import EpubVerifierInterface
from engineering_influence.models.publishing.path_relativizer import PathRelativizer
from engineering_influence.models.publishing.project_layout import ProjectLayout
from engineering_influence.services.epub.epub_builder import EpubBuilder
from engineering_influence.services.publishing.interfaces.pdf_verifier_interface import (
    PdfVerifierInterface,
)
from engineering_influence.services.release.interfaces.publish_steps_interface import (
    PublishStepsInterface,
)
from engineering_influence.services.typesetting.interfaces.book_builder_interface import (
    BookBuilderInterface,
)

Step = tuple[str, list[str], Callable[[], str]]


class PublishSteps(PublishStepsInterface):
    """Each action builds one artifact set and raises BookBuildError if its checks fail.

    The pre-package scripts ran their own verification after building; here it is explicit.
    """

    def __init__(
        self,
        layout: ProjectLayout,
        builder: BookBuilderInterface,
        pdf_verifier: PdfVerifierInterface,
        covers: CoverBuilderInterface,
        epub: EpubBuilder,
        loader: BookLoaderInterface,
        verifier: EpubVerifierInterface,
        strict_verifier: EpubVerifierInterface,
    ) -> None:
        """Remember the layout, builder, PDF verifier, covers, EPUB builder and loader the publication steps use."""
        self._layout = layout
        self._builder = builder
        self._pdf_verifier = pdf_verifier
        self._covers = covers
        self._epub = epub
        self._loader = loader
        self._verifier = verifier
        self._strict_verifier = strict_verifier
        self._relativizer = PathRelativizer(layout.root)

    def plan(self, slug: str, *, hardcover: bool, strict: bool = False) -> list[Step]:
        """The ordered steps: interior, optional hardcover interior, covers, then the EPUB."""
        steps: list[Step] = [("pdf", ["BookBuilder.build", slug], lambda: self.pdf(slug))]
        if hardcover:
            steps.append(
                (
                    "hardcover",
                    ["BookBuilder.build", slug, "--hardcover"],
                    lambda: self.hardcover(slug),
                )
            )
        cover_command = ["CoverBuilder.build", slug, "--preview"]
        if hardcover:
            cover_command += ["--hardcover-pdf", f"output/{slug}-hardcover.pdf"]
        steps.append(("covers", cover_command, lambda: self.covers(slug, hardcover=hardcover)))
        steps.append(("epub", ["EpubBuilder.build", slug], lambda: self.epub(slug, strict=strict)))
        return steps

    def pdf(self, slug: str) -> str:
        """Build and verify the paperback interior."""
        return self._interior(slug, self._builder.build(slug), slug)

    def hardcover(self, slug: str) -> str:
        """Build and verify the compact hardcover interior."""
        return self._interior(slug, self._builder.build(slug, hardcover=True), f"{slug}-hardcover")

    def covers(self, slug: str, *, hardcover: bool) -> str:
        """Build and verify every cover file, with previews."""
        hardcover_pdf = Path("output") / f"{slug}-hardcover.pdf" if hardcover else None
        out = self._covers.build(slug, preview=True, hardcover_pdf=hardcover_pdf)
        return f"[{slug}] covers written to {self._relativizer.relative(out)}\n[{slug}] all cover checks passed"

    def epub(self, slug: str, *, strict: bool = False) -> str:
        """Build and verify the EPUB; a strict release also requires epubcheck to run."""
        path = self._epub.build(slug)
        book = self._loader.load(self._layout.books / f"{slug}.toml")
        verifier = self._strict_verifier if strict else self._verifier
        self._raise_on(slug, verifier.verify(path, book))
        return f"[{slug}] built {self._relativizer.relative(path)}\n[{slug}] all checks passed"

    def _interior(self, slug: str, pdf: Path, log_slug: str) -> str:
        log = self._layout.build / log_slug / f"{slug}.log"
        self._raise_on(
            slug,
            self._pdf_verifier.verify(pdf, self._layout.books / f"{slug}.toml", log),
        )
        return f"[{slug}] built {self._relativizer.relative(pdf)}\n[{slug}] all checks passed"

    def _raise_on(self, slug: str, problems: list[str]) -> None:
        if problems:
            raise BookBuildError("\n".join(f"[{slug}] FAIL {problem}" for problem in problems))
