# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose the acceptance pipeline for a project, when a book is published."""

from engineering_influence.infrastructure.publishing.system_clock import SystemClock
from engineering_influence.infrastructure.release.epub_zip_check import EpubZipCheck
from engineering_influence.infrastructure.release.git_state import GitState
from engineering_influence.infrastructure.release.tool_versions import ToolVersions
from engineering_influence.interfaces.book_loader_interface import BookLoaderInterface
from engineering_influence.interfaces.build_workspace_interface import BuildWorkspaceInterface
from engineering_influence.interfaces.cover_builder_provider_interface import (
    CoverBuilderProviderInterface,
)
from engineering_influence.interfaces.epub_verifier_interface import EpubVerifierInterface
from engineering_influence.interfaces.manuscript_source_interface import ManuscriptSourceInterface
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
from engineering_influence.services.publishing.interfaces.pdf_verifier_interface import (
    PdfVerifierInterface,
)
from engineering_influence.services.release.publish_pipeline import PublishPipeline
from engineering_influence.services.release.publish_steps import PublishSteps
from engineering_influence.services.typesetting.interfaces.book_builder_interface import (
    BookBuilderInterface,
)


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
        builder: BookBuilderInterface,
        pdf_verifier: PdfVerifierInterface,
        epub: EpubBuilder,
        covers: CoverBuilderProviderInterface,
        qa: RenderQaInterface,
        verifier: EpubVerifierInterface,
        strict_verifier: EpubVerifierInterface,
    ) -> None:
        """Remember the config, file source, PDF inspector, loader and workspace one publication uses."""
        self._config = config
        self._files = files
        self._pdfs = pdfs
        self._loader = loader
        self._workspace = workspace
        self._builder = builder
        self._pdf_verifier = pdf_verifier
        self._epub = epub
        self._covers = covers
        self._qa = qa
        self._verifier = verifier
        self._strict_verifier = strict_verifier

    def provide(self) -> PublishPipelineInterface:
        """Build the pipeline, loading cover plugins as the build does."""
        layout = self._config.layout()
        steps = PublishSteps(
            layout,
            self._builder,
            self._pdf_verifier,
            self._covers.provide(),
            self._epub,
            self._loader,
            self._verifier,
            self._strict_verifier,
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
