# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose the publishing controller for a project."""

from pathlib import Path

from engineering_influence.controllers.publishing_controller import PublishingController
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
from engineering_influence.runtime.interfaces.publishing_controller_factory_interface import (
    PublishingControllerFactoryInterface,
)


class PublishingControllerFactory(PublishingControllerFactoryInterface):
    """Wire a controller to the real file system, PDF libraries and LaTeX toolchain."""

    def create(self, root: Path) -> PublishingController:
        """Load the project at ``root`` and wire its collaborators."""
        config = ProjectConfig.load(root)
        return PublishingController(
            config,
            FilesystemManuscriptSource(),
            PypdfPdfInspector(),
            BookLoader(config.root),
            FilesystemBuildWorkspace(),
            PackageAssets(),
            LatexCompiler(),
        )
