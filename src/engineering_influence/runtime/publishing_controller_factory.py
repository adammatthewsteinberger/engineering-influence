# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose the publishing controller for a project."""

from pathlib import Path

from engineering_influence.controllers.publishing_controller import PublishingController
from engineering_influence.infrastructure.epub.cover_image import CoverImage
from engineering_influence.infrastructure.epub.epub_archive import EpubArchive
from engineering_influence.infrastructure.epub.epub_cover_inspector import EpubCoverInspector
from engineering_influence.infrastructure.epub.epubcheck_runner import EpubcheckRunner
from engineering_influence.infrastructure.epub.tex4ebook_compiler import Tex4ebookCompiler
from engineering_influence.infrastructure.epub.zip_epub_package import ZipEpubPackage
from engineering_influence.infrastructure.publishing.directory_publisher import DirectoryPublisher
from engineering_influence.infrastructure.publishing.filesystem_manuscript_source import (
    FilesystemManuscriptSource,
)
from engineering_influence.infrastructure.publishing.package_assets import PackageAssets
from engineering_influence.infrastructure.publishing.pypdf_pdf_inspector import PypdfPdfInspector
from engineering_influence.infrastructure.qa.render_qa import RenderQa
from engineering_influence.infrastructure.typesetting.filesystem_build_workspace import (
    FilesystemBuildWorkspace,
)
from engineering_influence.infrastructure.typesetting.latex_compiler import LatexCompiler
from engineering_influence.models.publishing.project_config import ProjectConfig
from engineering_influence.repositories.release.artifact_inventory import ArtifactInventory
from engineering_influence.repositories.typesetting.book_loader import BookLoader
from engineering_influence.runtime.cover_builder_provider import CoverBuilderProvider
from engineering_influence.runtime.interfaces.publishing_controller_factory_interface import (
    PublishingControllerFactoryInterface,
)
from engineering_influence.runtime.publish_pipeline_provider import PublishPipelineProvider
from engineering_influence.services.epub.epub_builder import EpubBuilder
from engineering_influence.services.epub.epub_identifier import EpubIdentifier
from engineering_influence.services.epub.epub_repacker import EpubRepacker
from engineering_influence.services.epub.epub_verifier import EpubVerifier
from engineering_influence.services.package_book import PackageBook
from engineering_influence.services.publishing.pdf_verifier import PdfVerifier
from engineering_influence.services.typesetting.book_builder import BookBuilder


class PublishingControllerFactory(PublishingControllerFactoryInterface):
    """Wire a controller to the real file system, PDF libraries and LaTeX toolchain."""

    def create(self, root: Path) -> PublishingController:
        """Load the project at ``root`` and wire its collaborators."""
        config = ProjectConfig.load(root)
        layout = config.layout()
        files = FilesystemManuscriptSource()
        loader = BookLoader(config.root)
        workspace = FilesystemBuildWorkspace()
        assets = PackageAssets()
        identifier = EpubIdentifier()
        epub = EpubBuilder(
            layout,
            loader,
            Tex4ebookCompiler(),
            workspace,
            assets,
            EpubRepacker(CoverImage(layout), ZipEpubPackage(), identifier),
            files,
            identifier,
        )
        archive, inspector = EpubArchive(), EpubCoverInspector()
        epub_verifier = EpubVerifier(archive, EpubcheckRunner(), inspector)
        strict_verifier = EpubVerifier(archive, EpubcheckRunner(required=True), inspector)
        pdfs = PypdfPdfInspector()
        builder = BookBuilder(layout, loader, LatexCompiler(), workspace, assets, files)
        pdf_verifier = PdfVerifier(pdfs, files)
        covers = CoverBuilderProvider(config)
        qa = RenderQa(config.root)
        publisher = PublishPipelineProvider(
            config,
            files,
            pdfs,
            loader,
            workspace,
            builder,
            pdf_verifier,
            epub,
            covers,
            qa,
            epub_verifier,
            strict_verifier,
        )
        packager = PackageBook(
            config.layout(),
            ArtifactInventory(config.layout()),
            DirectoryPublisher(),
        )
        return PublishingController(
            config,
            files,
            pdfs,
            loader,
            builder,
            pdf_verifier,
            epub,
            epub_verifier,
            covers,
            qa,
            publisher,
            packager,
        )
