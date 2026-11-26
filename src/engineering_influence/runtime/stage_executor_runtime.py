# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Chooses what does a run's stages: the offline placeholder, or a model, only when told to."""

from collections.abc import Mapping
from datetime import date
from pathlib import Path

import httpx

from engineering_influence import __version__
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.audit.temp_project_manuscript_auditor import (
    TempProjectManuscriptAuditor,
)
from engineering_influence.infrastructure.author.toml_author_profile_loader import (
    TomlAuthorProfileLoader,
)
from engineering_influence.infrastructure.book_build.temp_project_manuscript_builder import (
    TempProjectManuscriptBuilder,
)
from engineering_influence.infrastructure.bundled_scripture import BundledScripture
from engineering_influence.infrastructure.deterministic_stage_executor import (
    DeterministicStageExecutor,
)
from engineering_influence.infrastructure.epub.epubcheck_runner import EpubcheckRunner
from engineering_influence.infrastructure.epub.temporary_screenplay_epub_writer import (
    TemporaryScreenplayEpubWriter,
)
from engineering_influence.infrastructure.epub.zip_epub_package import ZipEpubPackage
from engineering_influence.infrastructure.models.anthropic_model import AnthropicModel
from engineering_influence.infrastructure.models.openai_compatible_model import (
    OpenAICompatibleModel,
)
from engineering_influence.infrastructure.models.toml_model_catalog_loader import (
    TomlModelCatalogLoader,
)
from engineering_influence.infrastructure.models.toml_model_profile_loader import (
    TomlModelProfileLoader,
)
from engineering_influence.infrastructure.prompt_library.toml_prompt_library import (
    TomlPromptLibrary,
)
from engineering_influence.infrastructure.publishing.pypdf_pdf_inspector import PypdfPdfInspector
from engineering_influence.infrastructure.research.brave_search_provider import (
    BraveSearchProvider,
)
from engineering_influence.infrastructure.research.html_text_extractor import HtmlTextExtractor
from engineering_influence.infrastructure.research.http_source_fetcher import HttpSourceFetcher
from engineering_influence.infrastructure.research.searxng_search_provider import (
    SearxngSearchProvider,
)
from engineering_influence.infrastructure.security.public_https_url_pinner import (
    PublicHttpsUrlPinner,
)
from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)
from engineering_influence.infrastructure.skills.directory_skill_files import DirectorySkillFiles
from engineering_influence.infrastructure.skills.toml_skill_lock_store import TomlSkillLockStore
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.infrastructure.tools.http_mcp_transport_factory import (
    HttpMcpTransportFactory,
)
from engineering_influence.infrastructure.tools.sha256_file_hasher import Sha256FileHasher
from engineering_influence.infrastructure.tools.stdio_mcp_transport_factory import (
    StdioMcpTransportFactory,
)
from engineering_influence.infrastructure.tools.toml_tool_lock_store import TomlToolLockStore
from engineering_influence.infrastructure.typesetting.latex_compiler import LatexCompiler
from engineering_influence.infrastructure.typesetting.latex_screenplay_typesetter import (
    LatexScreenplayTypesetter,
)
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.book_publisher_interface import BookPublisherInterface
from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.interfaces.manuscript_builder_interface import ManuscriptBuilderInterface
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.interfaces.narrator_interface import NarratorInterface
from engineering_influence.interfaces.publish_pipeline_interface import PublishPipelineInterface
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.interfaces.source_fetcher_interface import SourceFetcherInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.stage_guidance_interface import StageGuidanceInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.author_profile import AuthorProfile
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.model_profile import ModelProfile
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.tool_limits import ToolLimits
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.runtime.controller_book_publisher import ControllerBookPublisher
from engineering_influence.runtime.controller_publish_pipeline import ControllerPublishPipeline
from engineering_influence.runtime.interfaces.stage_executor_runtime_interface import (
    StageExecutorRuntimeInterface,
)
from engineering_influence.services.acx_export_stage_executor import AcxExportStageExecutor
from engineering_influence.services.ask_model import AskModel
from engineering_influence.services.assemble_stage_executor import AssembleStageExecutor
from engineering_influence.services.audit_stage_executor import AuditStageExecutor
from engineering_influence.services.book_config_writer import BookConfigWriter
from engineering_influence.services.build_screenplay_epub_stage_executor import (
    BuildScreenplayEpubStageExecutor,
)
from engineering_influence.services.build_stage_executor import BuildStageExecutor
from engineering_influence.services.call_model import CallModel
from engineering_influence.services.chapter_cleaner import ChapterCleaner
from engineering_influence.services.content_policy import ContentPolicy
from engineering_influence.services.content_policy_stage_executor import (
    ContentPolicyStageExecutor,
)
from engineering_influence.services.context_assembler import ContextAssembler
from engineering_influence.services.continuity_checker import ContinuityChecker
from engineering_influence.services.cost_estimator import CostEstimator
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.dash_rewriter import DashRewriter
from engineering_influence.services.draft_stage_executor import DraftStageExecutor
from engineering_influence.services.fact_check_stage_executor import FactCheckStageExecutor
from engineering_influence.services.fact_claim_parser import FactClaimParser
from engineering_influence.services.fallback_search_provider import FallbackSearchProvider
from engineering_influence.services.fetch_url_tool import FetchUrlTool
from engineering_influence.services.fitting_model import FittingModel
from engineering_influence.services.fountain_parser import FountainParser
from engineering_influence.services.interfaces.cost_estimator_interface import (
    CostEstimatorInterface,
)
from engineering_influence.services.kind_stage_executor import KindStageExecutor
from engineering_influence.services.local_default_model import LocalDefaultModel
from engineering_influence.services.lock_shooting_script_stage_executor import (
    LockShootingScriptStageExecutor,
)
from engineering_influence.services.lock_stage_guidance import LockStageGuidance
from engineering_influence.services.lock_tool_grants import LockToolGrants
from engineering_influence.services.manuscript_project import ManuscriptProject
from engineering_influence.services.mcp_client_factory import McpClientFactory
from engineering_influence.services.mcp_server_launcher import McpServerLauncher
from engineering_influence.services.mcp_tool_factory import McpToolFactory
from engineering_influence.services.metadata_parser import MetadataParser
from engineering_influence.services.model_scene_drafter import ModelSceneDrafter
from engineering_influence.services.model_scene_reviser import ModelSceneReviser
from engineering_influence.services.model_stage_executor import ModelStageExecutor
from engineering_influence.services.narration_gate import NarrationGate
from engineering_influence.services.narration_stage_executor import NarrationStageExecutor
from engineering_influence.services.narration_text import NarrationText
from engineering_influence.services.no_stage_guidance import NoStageGuidance
from engineering_influence.services.nonfiction_output_checks import NonfictionOutputChecks
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.nonfiction_revision_passes import NonfictionRevisionPasses
from engineering_influence.services.novel_draft_checks import NovelDraftChecks
from engineering_influence.services.novel_output_checks import NovelOutputChecks
from engineering_influence.services.novel_recipes import NovelRecipes
from engineering_influence.services.novel_revision_passes import NovelRevisionPasses
from engineering_influence.services.outline_parser import OutlineParser
from engineering_influence.services.quality_report import QualityReport
from engineering_influence.services.read_skill_tool import ReadSkillTool
from engineering_influence.services.reference_parser import ReferenceParser
from engineering_influence.services.render_screenplay_stage_executor import (
    RenderScreenplayStageExecutor,
)
from engineering_influence.services.revision_report_stage_executor import (
    RevisionReportStageExecutor,
)
from engineering_influence.services.revision_report_writer import RevisionReportWriter
from engineering_influence.services.revision_stage_executor import RevisionStageExecutor
from engineering_influence.services.run_tool_loop import RunToolLoop
from engineering_influence.services.scene_card_list import SceneCardList
from engineering_influence.services.screenplay_assemble_stage_executor import (
    ScreenplayAssembleStageExecutor,
)
from engineering_influence.services.screenplay_assembler import ScreenplayAssembler
from engineering_influence.services.screenplay_draft_stage_executor import (
    ScreenplayDraftStageExecutor,
)
from engineering_influence.services.screenplay_epub_package import ScreenplayEpubPackage
from engineering_influence.services.screenplay_latex_source import ScreenplayLatexSource
from engineering_influence.services.screenplay_length import ScreenplayLength
from engineering_influence.services.screenplay_output_checks import ScreenplayOutputChecks
from engineering_influence.services.screenplay_recipes import ScreenplayRecipes
from engineering_influence.services.screenplay_revise_stage_executor import (
    ScreenplayReviseStageExecutor,
)
from engineering_influence.services.screenplay_section_check import ScreenplaySectionCheck
from engineering_influence.services.scripture_checker import ScriptureChecker
from engineering_influence.services.scripture_draft_checks import ScriptureDraftChecks
from engineering_influence.services.shooting_lock_codec import ShootingLockCodec
from engineering_influence.services.shooting_lock_planner import ShootingLockPlanner
from engineering_influence.services.shooting_script_renderer import ShootingScriptRenderer
from engineering_influence.services.skill_lock_verifier import SkillLockVerifier
from engineering_influence.services.spend_guard import SpendGuard
from engineering_influence.services.stage_executor_router import StageExecutorRouter
from engineering_influence.services.story_bible_parser import StoryBibleParser
from engineering_influence.services.tool_lock_verifier import ToolLockVerifier
from engineering_influence.services.tool_registry import ToolRegistry
from engineering_influence.services.tool_runner import ToolRunner
from engineering_influence.services.tool_server_fleet import ToolServerFleet
from engineering_influence.services.verbatim_dashes import VerbatimDashes
from engineering_influence.services.web_search_tool import WebSearchTool


class StageExecutorRuntime(StageExecutorRuntimeInterface):
    """``EI_STAGE_EXECUTOR`` picks ``local`` (the default), ``model`` or ``deterministic``.

    ``local`` is free: ``LocalDefaultModel`` is an open-source model served on this machine, with a SearXNG on
    ``http://127.0.0.1:8888`` for the research stage unless ``EI_SEARXNG_URL`` or ``BRAVE_SEARCH_API_KEY`` says
    otherwise. It needs no profile or catalog file, and building it contacts nothing: a missing server shows when a
    stage calls it (``ei doctor`` checks first). ``deterministic`` is the offline placeholder, for tests and
    for trying the plumbing with no model at all.

    ``model`` spends money, so it is never inferred from a profile file being there. It needs
    ``EI_STAGE_MODEL_PROFILE`` (the profile's name), ``EI_MODEL_PROFILES`` and ``EI_MODEL_CATALOG``
    (the files ``ei doctor --models`` checks), the profile's key, and a web search for the
    research stage: ``EI_SEARXNG_URL`` (a SearXNG instance, tried first), ``BRAVE_SEARCH_API_KEY``
    (Brave, the backup, or the only search when there is no instance), or both. Anything missing, an unknown
    profile, no price in force today, or a key that would cross a network in clear stops the
    process at start, before any call is made. The price is looked up once, at start.

    ``EI_TOOL_LOCK`` names a tool lock ([TOOL_LOCK.md](../../../docs/TOOL_LOCK.md)). Its servers are
    started and verified here, a changed one stops the process, and a stage is offered only the
    locked tools the lock grants it.

    ``EI_AUTHOR_PROFILE`` names the author's own details ([BOOKS_AND_KDP.md](../../../docs/BOOKS_AND_KDP.md)),
    which the assemble stage writes into the book's config; they are never sent to a model.

    ``EI_SKILL_LOCK`` names a skill lock ([SKILLS.md](../../../docs/SKILLS.md)). Each skill enabled for a
    stage is checked against its hash here, before any tool server is started, and a changed one stops the
    process; a stage's prompt then carries only the skills the lock enables for it.
    """

    CONNECT_TIMEOUT_SECONDS = 10.0
    RESEARCH_TIMEOUT_SECONDS = 30.0
    SERVER_SESSION_SECONDS = 4 * 3600.0
    SERVER_REQUEST_SECONDS = 30.0
    SERVER_MEMORY_BYTES = 2 * 1024**3
    SERVER_DISK_BYTES = 1024**3
    LOCAL_SEARXNG = "http://127.0.0.1:8888"

    def __init__(
        self,
        environment: Mapping[str, str],
        secrets: SecretProviderInterface,
        today: date,
        request_timeout_seconds: float = 1_800.0,
        builder: ManuscriptBuilderInterface | None = None,
    ) -> None:
        self._environment = environment
        self._secrets = secrets
        self._today = today
        self._timeout = request_timeout_seconds
        self._builder = builder
        self._client: httpx.Client | None = None
        self._research_client: httpx.Client | None = None
        self._runner: ToolRunner | None = None
        self._fleet: ToolServerFleet | None = None
        self._free = False
        self._estimator: CostEstimatorInterface | None = None

    def build(
        self, artifacts: ArtifactStoreInterface, journal: JournalInterface
    ) -> StageExecutorInterface:
        """The free local model by default, the offline placeholder, or a model of your own when the environment says so."""
        kind = self._environment.get("EI_STAGE_EXECUTOR", "local")
        if kind == "deterministic":
            return DeterministicStageExecutor(artifacts, journal)
        if kind not in ("local", "model"):
            raise ApplicationError(
                code="STAGE_EXECUTOR_UNKNOWN",
                message=f"EI_STAGE_EXECUTOR is {kind!r}; use 'local', 'model' or 'deterministic'",
                http_status=503,
            )
        self._free = kind == "local"
        model = self._local_model() if self._free else self._model()
        guidance, skill_tools = self._guidance()
        lock, locked_tools = self._locked_servers()
        search, fetcher = self._research()
        tools = ToolRegistry(
            (WebSearchTool(search), FetchUrlTool(fetcher), *locked_tools, *skill_tools)
        )
        limits = ToolLoopLimits()
        runner = ToolRunner(tools, journal, limits)
        self._runner = runner
        ask = AskModel(CallModel(model, journal), model)
        prompts = TomlPromptLibrary()
        loop = RunToolLoop(ask, runner, limits)
        outlines = OutlineParser()
        dashes = DashRewriter()
        metadata = MetadataParser(dashes)
        profile = self._author_profile()
        revisions = NonfictionRevisionPasses()
        novel_revisions = NovelRevisionPasses()
        descriptor = model.describe()
        estimator = CostEstimator(
            descriptor,
            {
                BookKind.NONFICTION: NonfictionRecipes(),
                BookKind.NOVEL: NovelRecipes(),
                BookKind.SCREENPLAY: ScreenplayRecipes(),
            },
            CreateRun.PLANS,
        )
        self._estimator = estimator
        drafter = DraftStageExecutor(
            artifacts,
            prompts,
            outlines,
            ContextAssembler(FittingModel(model), prompts.get("context_pack")),
            loop,
            guidance,
            SpendGuard,
            descriptor.context_window,
            descriptor.max_output_tokens,
            tools,
            checks=ScriptureDraftChecks(
                ScriptureChecker(BundledScripture(), ReferenceParser()),
            ),
        )
        novel_drafter = ContentPolicyStageExecutor(
            DraftStageExecutor(
                artifacts,
                prompts,
                outlines,
                ContextAssembler(FittingModel(model), prompts.get("novel_context_pack")),
                loop,
                guidance,
                SpendGuard,
                descriptor.context_window,
                descriptor.max_output_tokens,
                tools,
                NovelRecipes.DRAFT,
                NovelDraftChecks(StoryBibleParser(), ContinuityChecker()),
            ),
            ContentPolicy(),
            descriptor,
        )
        grants = LockToolGrants(lock)
        nonfiction = ModelStageExecutor(
            NonfictionRecipes(),
            prompts,
            artifacts,
            loop,
            tools,
            grants,
            guidance,
            NonfictionOutputChecks(outlines, metadata),
            SpendGuard,
        )
        novel = ContentPolicyStageExecutor(
            ModelStageExecutor(
                NovelRecipes(),
                prompts,
                artifacts,
                loop,
                tools,
                grants,
                guidance,
                NovelOutputChecks(StoryBibleParser(), outlines, metadata),
                SpendGuard,
            ),
            ContentPolicy(),
            descriptor,
        )
        screenplay = ModelStageExecutor(
            ScreenplayRecipes(),
            prompts,
            artifacts,
            loop,
            tools,
            grants,
            guidance,
            ScreenplayOutputChecks(),
            SpendGuard,
        )
        revising: dict[str, dict[BookKind, StageExecutorInterface]] = {}
        for editing in revisions.passes():
            revising.setdefault(editing.stage, {})[BookKind.NONFICTION] = RevisionStageExecutor(
                editing,
                artifacts,
                prompts,
                outlines,
                loop,
                guidance,
                SpendGuard,
                descriptor.context_window,
                descriptor.max_output_tokens,
                tools,
            )
        for editing in novel_revisions.passes():
            # Only the last pass is read against the story bible again: that is the text the book is built from.
            last = editing.output == novel_revisions.final()
            revision = RevisionStageExecutor(
                editing,
                artifacts,
                prompts,
                outlines,
                loop,
                guidance,
                SpendGuard,
                descriptor.context_window,
                descriptor.max_output_tokens,
                tools,
                voice_source="brief.md",
                checks=NovelDraftChecks(StoryBibleParser(), ContinuityChecker()) if last else None,
            )
            revising.setdefault(editing.stage, {})[BookKind.NOVEL] = ContentPolicyStageExecutor(
                revision, ContentPolicy(), descriptor
            )
        fact_checker = FactCheckStageExecutor(
            artifacts,
            prompts,
            outlines,
            loop,
            SpendGuard,
            search,
            fetcher,
            FactClaimParser(),
            descriptor.max_output_tokens,
        )
        return StageExecutorRouter(
            KindStageExecutor(
                {
                    BookKind.NONFICTION: nonfiction,
                    BookKind.NOVEL: novel,
                    BookKind.SCREENPLAY: screenplay,
                }
            ),
            {
                DraftStageExecutor.STAGE: KindStageExecutor(
                    {
                        BookKind.NONFICTION: drafter,
                        BookKind.NOVEL: novel_drafter,
                        BookKind.SCREENPLAY: ScreenplayDraftStageExecutor(
                            artifacts,
                            ModelSceneDrafter(prompts, loop, SpendGuard),
                            SceneCardList(),
                            ScreenplaySectionCheck(FountainParser()),
                        ),
                    }
                ),
                ScreenplayReviseStageExecutor.STAGE: KindStageExecutor(
                    {
                        BookKind.SCREENPLAY: ScreenplayReviseStageExecutor(
                            artifacts,
                            ModelSceneReviser(prompts, loop, SpendGuard),
                            SceneCardList(),
                            ScreenplaySectionCheck(FountainParser()),
                        ),
                    }
                ),
                RenderScreenplayStageExecutor.STAGE: KindStageExecutor(
                    {
                        BookKind.SCREENPLAY: RenderScreenplayStageExecutor(
                            artifacts,
                            ScreenplayLatexSource(FountainParser()),
                            LatexScreenplayTypesetter(LatexCompiler(), PypdfPdfInspector()),
                            ScreenplayLength(),
                        ),
                    }
                ),
                BuildScreenplayEpubStageExecutor.STAGE: KindStageExecutor(
                    {
                        BookKind.SCREENPLAY: BuildScreenplayEpubStageExecutor(
                            artifacts,
                            ScreenplayEpubPackage(FountainParser()),
                            TemporaryScreenplayEpubWriter(ZipEpubPackage(), EpubcheckRunner()),
                        ),
                    }
                ),
                ScreenplayAssembleStageExecutor.STAGE: KindStageExecutor(
                    {
                        BookKind.SCREENPLAY: ScreenplayAssembleStageExecutor(
                            artifacts,
                            SceneCardList(),
                            ScreenplayAssembler(FountainParser()),
                            FountainParser(),
                        ),
                    }
                ),
                LockShootingScriptStageExecutor.STAGE: KindStageExecutor(
                    {
                        BookKind.SCREENPLAY: LockShootingScriptStageExecutor(
                            artifacts,
                            SceneCardList(),
                            FountainParser(),
                            ShootingLockPlanner(),
                            ShootingLockCodec(),
                            ShootingScriptRenderer(FountainParser()),
                        ),
                    }
                ),
                RevisionReportStageExecutor.STAGE: KindStageExecutor(
                    {
                        BookKind.SCREENPLAY: RevisionReportStageExecutor(
                            artifacts,
                            SceneCardList(),
                            ShootingLockCodec(),
                            RevisionReportWriter(),
                        ),
                    }
                ),
                **{stage: KindStageExecutor(by_kind) for stage, by_kind in revising.items()},
                FactCheckStageExecutor.STAGE: KindStageExecutor(
                    {BookKind.NONFICTION: fact_checker}
                ),
                AcxExportStageExecutor.STAGE: KindStageExecutor(
                    {
                        BookKind.NONFICTION: AcxExportStageExecutor(
                            artifacts,
                            outlines,
                            NarrationText(),
                            MetadataParser(dashes),
                            profile.author if profile is not None else "",
                            self._narrator(self._environment),
                            NarrationGate(),
                        )
                    }
                ),
                NarrationStageExecutor.STAGE: KindStageExecutor(
                    {
                        BookKind.NONFICTION: NarrationStageExecutor(
                            artifacts,
                            outlines,
                            self._narrator(self._environment),
                            NarrationText(),
                            NarrationGate(),
                        )
                    }
                ),
                AssembleStageExecutor.STAGE: KindStageExecutor(
                    {
                        BookKind.NONFICTION: AssembleStageExecutor(
                            artifacts,
                            outlines,
                            metadata,
                            ChapterCleaner(dashes),
                            BookConfigWriter(),
                            profile,
                            FactCheckStageExecutor.OUTPUT,
                        ),
                        # A novel is assembled from its last editing pass, and keeps the dashes its prose has:
                        # only non-fiction refuses them.
                        BookKind.NOVEL: AssembleStageExecutor(
                            artifacts,
                            outlines,
                            metadata,
                            ChapterCleaner(VerbatimDashes()),
                            BookConfigWriter(),
                            profile,
                            novel_revisions.final(),
                        ),
                    }
                ),
                AuditStageExecutor.STAGE: AuditStageExecutor(
                    artifacts,
                    TempProjectManuscriptAuditor(self._pipeline),
                    ManuscriptProject(artifacts),
                ),
                BuildStageExecutor.STAGE: BuildStageExecutor(
                    artifacts,
                    self._book_builder(),
                    ManuscriptProject(artifacts),
                    QualityReport(),
                    estimator,
                ),
            },
        )

    def close(self) -> None:
        """Close the HTTP client and the tool threads behind a model-backed executor, if built."""
        if self._runner is not None:
            self._runner.close()
            self._runner = None
        if self._fleet is not None:
            self._fleet.close()
            self._fleet = None
        for client in (self._client, self._research_client):
            if client is not None:
                client.close()
        self._client = None
        self._research_client = None

    @staticmethod
    def _pipeline(root: Path) -> PublishPipelineInterface:
        """The acceptance pipeline for the project at ``root``.

        The publishing libraries (Pillow, numpy, the PDF readers) are imported here, when an audit runs, so a
        process that never audits a book does not need the ``publishing`` extra.
        """
        from engineering_influence.runtime.publishing_controller_factory import (
            PublishingControllerFactory,
        )

        return ControllerPublishPipeline(PublishingControllerFactory().create(root))

    def _book_builder(self) -> ManuscriptBuilderInterface:
        """The builder a test injected, or the real one.

        The real one builds every book as the pipeline does. It builds a strict release only when
        ``EI_BUILD_STRICT_RELEASE`` is ``1``, ``true`` or ``yes``: a strict release needs the author's pricing inputs,
        which a run cannot invent, so without them a missing price is a warning in the quality report.
        """
        if self._builder is not None:
            return self._builder
        return TempProjectManuscriptBuilder(self._publisher, strict_release=self.strict_release())

    def model(self) -> ModelInterface:
        """The model the environment names (``local`` or ``model``), without building any stage, for a caller that only needs to ask it.

        The evaluation's judge is built this way, from an environment whose ``EI_STAGE_MODEL_PROFILE`` names the judge's
        profile. The offline placeholder has no model and is refused. Close the runtime when the model is no longer needed.
        """
        kind = self._environment.get("EI_STAGE_EXECUTOR", "local")
        if kind not in ("local", "model"):
            raise ApplicationError(
                code="STAGE_EXECUTOR_UNKNOWN",
                message=f"EI_STAGE_EXECUTOR is {kind!r}; a model needs 'local' or 'model'",
                http_status=503,
            )
        self._free = kind == "local"
        return self._local_model() if self._free else self._model()

    def estimator(self) -> CostEstimatorInterface | None:
        """What a book is expected to cost with the model this runtime built, or None when no model is used."""
        return self._estimator

    def strict_release(self) -> bool:
        """Whether ``EI_BUILD_STRICT_RELEASE`` asks the build stage for a strict release (``1``, ``true`` or ``yes``)."""
        return self._environment.get("EI_BUILD_STRICT_RELEASE", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )

    def author_profile(self) -> AuthorProfile | None:
        """The author's details ``EI_AUTHOR_PROFILE`` names, or None; a named file that is not a profile is refused."""
        return self._author_profile()

    @staticmethod
    def _publisher(root: Path) -> BookPublisherInterface:
        """The publisher for the book project at ``root``: every gate, and the release bundle.

        The publishing libraries are imported here, when a book is built, so a process that never builds one does
        not need the ``publishing`` extra, a TeX toolchain or epubcheck.
        """
        from engineering_influence.runtime.publishing_controller_factory import (
            PublishingControllerFactory,
        )

        return ControllerBookPublisher(PublishingControllerFactory().create(root))

    def _author_profile(self) -> AuthorProfile | None:
        """The author's details from the file ``EI_AUTHOR_PROFILE`` names, if it names one.

        A profile is read only when it is named, so a stray file in the working directory adds nothing to a
        book. A named file that is missing, or is not a profile, stops the process at start, before any call
        is made. The details go into the book's config and are never sent to a model.
        """
        named = self._environment.get("EI_AUTHOR_PROFILE", "").strip()
        if not named:
            return None
        profile = TomlAuthorProfileLoader().load(Path(named))
        if profile is None:
            raise ApplicationError(
                code="AUTHOR_PROFILE_MISSING",
                message=f"EI_AUTHOR_PROFILE names {named}, which does not exist",
                http_status=503,
            )
        return profile

    def _guidance(self) -> tuple[StageGuidanceInterface, tuple[ToolInterface, ...]]:
        """The skills in the lock that ``EI_SKILL_LOCK`` names, checked against their hashes.

        A lock is read only when it is named, so a stray file in the working directory adds nothing
        to a prompt. A skill that is not the text the lock approved stops the process at start, before
        any tool server is started or any call is made. The skills are read once, here, so every stage of
        the run sees the same text. The second thing returned is the read-only ``read_skill`` tool, which
        serves the reference sections of those same verified skills to the stages that list them.
        """
        named = self._environment.get("EI_SKILL_LOCK", "").strip()
        if not named:
            return NoStageGuidance(), ()
        path = Path(named)
        lock = TomlSkillLockStore().load(path)
        if lock is None:
            raise ApplicationError(
                code="SKILL_LOCK_MISSING",
                message=f"EI_SKILL_LOCK names {named}, which does not exist",
                http_status=503,
            )
        verifier = SkillLockVerifier(DirectorySkillFiles(), TomlSkillParser())
        skills = verifier.verified(lock, path.parent / "skills")
        guidance = LockStageGuidance(lock, skills, TomlPromptLibrary().get("skill_guidance"))
        return guidance, (ReadSkillTool(skills),)

    def _locked_servers(self) -> tuple[ToolLock, tuple[ToolInterface, ...]]:
        """The servers in the lock that ``EI_TOOL_LOCK`` names, started and verified, and their tools.

        A lock is read only when it is named: a stray file in the working directory starts nothing.
        A server that is not what the lock approved stops the process at start.
        """
        named = self._environment.get("EI_TOOL_LOCK", "").strip()
        if not named:
            return ToolLock(), ()
        lock = TomlToolLockStore().load(Path(named))
        if lock is None:
            raise ApplicationError(
                code="TOOL_LOCK_MISSING",
                message=f"EI_TOOL_LOCK names {named}, which does not exist",
                http_status=503,
            )
        limits = ToolLimits(
            timeout_seconds=self.SERVER_SESSION_SECONDS,
            max_memory_bytes=self.SERVER_MEMORY_BYTES,
            max_disk_bytes=self.SERVER_DISK_BYTES,
        )
        launcher = McpServerLauncher(
            StdioMcpTransportFactory(limits, self._environment),
            HttpMcpTransportFactory(
                self._server_client,
                PublicHttpsUrlPinner(PublicHttpsUrlPolicy()),
                self._environment,
                self.SERVER_REQUEST_SECONDS,
                self.SERVER_SESSION_SECONDS,
            ),
            McpClientFactory("engineering-influence", __version__, self.SERVER_REQUEST_SECONDS),
            ToolLockVerifier(Sha256FileHasher()),
        )
        fleet = ToolServerFleet(launcher, McpToolFactory())
        fleet.start(lock)
        self._fleet = fleet
        return lock, fleet.tools()

    def _server_client(self) -> httpx.Client:
        """A client for one remote tool server: it owns its connection pool and is closed with the session."""
        return httpx.Client(
            timeout=httpx.Timeout(self.SERVER_REQUEST_SECONDS, connect=self.CONNECT_TIMEOUT_SECONDS)
        )

    @staticmethod
    def _narrator(environment: Mapping[str, str]) -> NarratorInterface | None:
        """The narrator for the non-Audible audiobook: none unless ``EI_NARRATOR`` names one.

        No engine is built into this release yet (ADR 0014 follows a listening test on the Mac). Naming one is refused
        now, rather than producing a book without the audio that was asked for.
        """
        name = environment.get("EI_NARRATOR", "").strip()
        if not name:
            return None
        raise ApplicationError(
            code="NARRATOR_UNAVAILABLE",
            message=(
                f"the narrator {name!r} is not in this build: its engine follows the listening test in "
                "docs/adr/0014-audiobook-narration-uses-kokoro-via-mlx-audio.md"
            ),
            http_status=503,
        )

    def _research(self) -> tuple[SearchProviderInterface, SourceFetcherInterface]:
        """The web search and the page reader, which the research stage and the fact checker share."""
        client = httpx.Client(
            timeout=httpx.Timeout(
                self.RESEARCH_TIMEOUT_SECONDS, connect=self.CONNECT_TIMEOUT_SECONDS
            )
        )
        self._research_client = client
        fetcher = HttpSourceFetcher(
            client, PublicHttpsUrlPinner(PublicHttpsUrlPolicy()), HtmlTextExtractor()
        )
        return self._search(client), fetcher

    def _search(self, client: httpx.Client) -> SearchProviderInterface:
        """SearXNG first when ``EI_SEARXNG_URL`` is set, Brave behind it when its key is set."""
        providers: list[SearchProviderInterface] = []
        address = self._environment.get("EI_SEARXNG_URL", "").strip()
        if address:
            try:
                providers.append(SearxngSearchProvider(client, address))
            except ValueError as error:
                raise ApplicationError(
                    code="STAGE_SEARXNG_URL_INVALID",
                    message=f"EI_SEARXNG_URL is not usable: {error}",
                    http_status=503,
                ) from error
        brave_key = self._brave_key()
        if brave_key:
            providers.append(BraveSearchProvider(client, brave_key))
        if not providers and self._free:
            providers.append(SearxngSearchProvider(client, self.LOCAL_SEARXNG))
        if not providers:
            raise ApplicationError(
                code="STAGE_SEARCH_NOT_CONFIGURED",
                message="the research stage needs a web search: set EI_SEARXNG_URL (a SearXNG "
                "instance) or BRAVE_SEARCH_API_KEY",
                http_status=503,
            )
        if len(providers) == 1:
            return providers[0]
        return FallbackSearchProvider(providers[0], providers[1])

    def _brave_key(self) -> str:
        try:
            return self._secrets.require("BRAVE_SEARCH_API_KEY").strip()
        except ApplicationError:
            return ""

    def _local_model(self) -> ModelInterface:
        free = LocalDefaultModel(self._environment)
        profile = free.profile()
        client = httpx.Client(
            timeout=httpx.Timeout(self._timeout, connect=self.CONNECT_TIMEOUT_SECONDS)
        )
        self._client = client
        return self._adapter(client, profile, "", free.descriptor())

    def _model(self) -> ModelInterface:
        name = self._required("EI_STAGE_MODEL_PROFILE")
        profiles_path = self._required("EI_MODEL_PROFILES")
        catalog_path = self._required("EI_MODEL_CATALOG")
        profiles = TomlModelProfileLoader().load(Path(profiles_path))
        profile = next((p for p in profiles if p.name == name), None)
        if profile is None:
            known = ", ".join(sorted(p.name for p in profiles))
            raise ApplicationError(
                code="STAGE_MODEL_PROFILE_UNKNOWN",
                message=f"no profile named {name!r} in {profiles_path} (it has: {known})",
                http_status=503,
            )
        if profile.sends_key_in_clear():
            raise ApplicationError(
                code="STAGE_MODEL_KEY_IN_CLEAR",
                message=f"profile {name!r} would send its key over plain http to another host",
                http_status=503,
            )
        descriptor = (
            TomlModelCatalogLoader()
            .load(Path(catalog_path))
            .descriptor(profile.provider, profile.model, self._today)
        )
        key = self._secrets.require(profile.api_key_env) if profile.requires_key() else ""
        client = httpx.Client(
            timeout=httpx.Timeout(self._timeout, connect=self.CONNECT_TIMEOUT_SECONDS)
        )
        self._client = client
        return self._adapter(client, profile, key, descriptor)

    @staticmethod
    def _adapter(
        client: httpx.Client, profile: ModelProfile, key: str, descriptor: ProviderDescriptor
    ) -> ModelInterface:
        if profile.adapter == "anthropic":
            return AnthropicModel(client, key, descriptor, profile.base_url)
        return OpenAICompatibleModel(
            client,
            key,
            descriptor,
            profile.base_url,
            profile.output_cap_field,
            profile.reasoning_effort,
        )

    def _required(self, name: str) -> str:
        value = self._environment.get(name, "").strip()
        if not value:
            raise ApplicationError(
                code="STAGE_MODEL_NOT_CONFIGURED",
                message=f"EI_STAGE_EXECUTOR=model needs {name}",
                http_status=503,
            )
        return value
