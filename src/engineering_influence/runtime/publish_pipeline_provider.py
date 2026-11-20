# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose the acceptance pipeline for a project, when a book is published."""

from engineering_influence.infrastructure.epub.epub_archive import EpubArchive
from engineering_influence.infrastructure.epub.epub_cover_inspector import EpubCoverInspector
from engineering_influence.infrastructure.epub.epubcheck_runner import EpubcheckRunner
from engineering_influence.infrastructure.publishing.system_clock import SystemClock
from engineering_influence.infrastructure.release.epub_zip_check import EpubZipCheck
from engineering_influence.infrastructure.release.git_state import GitState
from engineering_influence.infrastructure.release.tool_versions import ToolVersions
from engineering_influence.interfaces.book_loader_interface import BookLoaderInterface
from engineering_influence.interfaces.build_workspace_interface import BuildWorkspaceInterface
from engineering_influence.interfaces.cover_builder_provider_interface import (
    CoverBuilderProviderInterface,
)
from engineering_influence.interfaces.latex_compiler_interface import LatexCompilerInterface
from engineering_influence.interfaces.manuscript_source_interface import ManuscriptSourceInterface
from engineering_influence.interfaces.package_assets_interface import PackageAssetsInterface
from engineering_influence.interfaces.pdf_inspector_interface import PdfInspectorInterface
from engineering_influence.interfaces.publish_pipeline_interface import PublishPipelineInterface
from engineering_influence.interfaces.publish_pipeline_provider_interface import (
    PublishPipelineProviderInterface,
)
from engineering_influence.interfaces.render_qa_interface import RenderQaInterface
from engineering_influence.models.publishing.path_relativizer import PathRelativizer
from engineering_influence.models.publishing.project_config import ProjectConfig
from engineering_influence.repositories.release.artifact_inventory import ArtifactInventory
from engineering_influence.repositories.release.json_report import JsonReport
from engineering_influence.repositories.release.step_recorder import StepRecorder
from engineering_influence.services.epub.epub_builder import EpubBuilder
from engineering_influence.services.epub.epub_verifier import EpubVerifier
from engineering_influence.services.release.publish_pipeline import PublishPipeline
from engineering_influence.services.release.publish_steps import PublishSteps
from engineering_influence.services.typesetting.book_builder import BookBuilder


class PublishPipelineProvider(PublishPipelineProviderInterface):
    """Builds the cover builder, the steps and the evidence writers for one publication.

    The cover plugins load when the pipeline is provided, which is the start of ``publish``, so a
    broken plugin fails the command before any report is written, as it always has.
    """

    def __init__(
        self,
        config: ProjectConfig,
        files: ManuscriptSourceInterface,
        pdfs: PdfInspectorInterface,
        loader: BookLoaderInterface,
        workspace: BuildWorkspaceInterface,
        assets: PackageAssetsInterface,
        latex: LatexCompilerInterface,
        epub: EpubBuilder,
        covers: CoverBuilderProviderInterface,
        qa: RenderQaInterface,
    ) -> None:
        self._config = config
        self._files = files
        self._pdfs = pdfs
        self._loader = loader
        self._workspace = workspace
        self._assets = assets
        self._latex = latex
        self._epub = epub
        self._covers = covers
        self._qa = qa

    def provide(self) -> PublishPipelineInterface:
        """Build the pipeline, loading cover plugins as the build does."""
        layout = self._config.layout()
        builder = BookBuilder(
            layout, self._loader, self._latex, self._workspace, self._assets, self._files
        )
        archive, inspector = EpubArchive(), EpubCoverInspector()
        steps = PublishSteps(
            layout,
            builder,
            self._covers.provide(),
            self._epub,
            self._files,
            self._pdfs,
            self._loader,
            EpubVerifier(archive, EpubcheckRunner(), inspector),
            EpubVerifier(archive, EpubcheckRunner(required=True), inspector),
        )
        clock = SystemClock()
        return PublishPipeline(
            layout,
            steps,
            self._files,
            self._pdfs,
            self._qa,
            clock,
            JsonReport(),
            ArtifactInventory(layout),
            GitState(layout.root),
            ToolVersions(),
            EpubZipCheck(),
            StepRecorder(PathRelativizer(layout.root), clock),
            self._workspace,
        )
