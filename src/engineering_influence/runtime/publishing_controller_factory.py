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
from engineering_influence.infrastructure.publishing.filesystem_manuscript_source import (
    FilesystemManuscriptSource,
)
from engineering_influence.infrastructure.publishing.package_assets import PackageAssets
from engineering_influence.infrastructure.publishing.pypdf_pdf_inspector import PypdfPdfInspector
from engineering_influence.infrastructure.typesetting.filesystem_build_workspace import (
    FilesystemBuildWorkspace,
)
from engineering_influence.infrastructure.typesetting.latex_compiler import LatexCompiler
from engineering_influence.models.publishing.project_config import ProjectConfig
from engineering_influence.repositories.typesetting.book_loader import BookLoader
from engineering_influence.runtime.cover_builder_provider import CoverBuilderProvider
from engineering_influence.runtime.interfaces.publishing_controller_factory_interface import (
    PublishingControllerFactoryInterface,
)
from engineering_influence.services.epub.epub_builder import EpubBuilder
from engineering_influence.services.epub.epub_identifier import EpubIdentifier
from engineering_influence.services.epub.epub_repacker import EpubRepacker
from engineering_influence.services.epub.epub_verifier import EpubVerifier


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
        epub_verifier = EpubVerifier(EpubArchive(), EpubcheckRunner(), EpubCoverInspector())
        return PublishingController(
            config,
            files,
            PypdfPdfInspector(),
            loader,
            workspace,
            assets,
            LatexCompiler(),
            epub,
            epub_verifier,
            CoverBuilderProvider(config),
        )
