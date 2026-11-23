# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Compose the command-line application."""

import os
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from engineering_influence import __version__
from engineering_influence.controllers.interfaces.run_controller_interface import (
    RunControllerInterface,
)
from engineering_influence.controllers.project_controller import ProjectController
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.plugins.directory_plugin_folder_reader import (
    DirectoryPluginFolderReader,
)
from engineering_influence.infrastructure.plugins.json_marketplace_parser import (
    JsonMarketplaceParser,
)
from engineering_influence.infrastructure.plugins.lazy_bundle_fetcher import LazyBundleFetcher
from engineering_influence.infrastructure.plugins.toml_plugin_index_parser import (
    TomlPluginIndexParser,
)
from engineering_influence.infrastructure.plugins.toml_plugin_lock_store import (
    TomlPluginLockStore,
)
from engineering_influence.infrastructure.plugins.toml_plugin_parser import TomlPluginParser
from engineering_influence.infrastructure.plugins.toml_plugin_writer import TomlPluginWriter
from engineering_influence.infrastructure.skills.directory_skill_files import DirectorySkillFiles
from engineering_influence.infrastructure.skills.file_skill_source import FileSkillSource
from engineering_influence.infrastructure.skills.new_file_skill_sink import NewFileSkillSink
from engineering_influence.infrastructure.skills.toml_skill_lock_store import TomlSkillLockStore
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.infrastructure.skills.toml_skill_writer import TomlSkillWriter
from engineering_influence.infrastructure.tools.lazy_remote_transport_factory import (
    LazyRemoteTransportFactory,
)
from engineering_influence.infrastructure.tools.path_executable_finder import PathExecutableFinder
from engineering_influence.infrastructure.tools.sha256_file_hasher import Sha256FileHasher
from engineering_influence.infrastructure.tools.stdio_mcp_transport_factory import (
    StdioMcpTransportFactory,
)
from engineering_influence.infrastructure.tools.toml_tool_lock_store import TomlToolLockStore
from engineering_influence.interactions.cli.book_cli import BookCli
from engineering_influence.interactions.cli.cli_application import CliApplication
from engineering_influence.interactions.cli.db_cli import DbCli
from engineering_influence.interactions.cli.doctor_cli import DoctorCli
from engineering_influence.interactions.cli.interfaces.cli_application_interface import (
    CliApplicationInterface,
)
from engineering_influence.interactions.cli.plugins_cli import PluginsCli
from engineering_influence.interactions.cli.run_cli import RunCli
from engineering_influence.interactions.cli.serve_cli import ServeCli
from engineering_influence.interactions.cli.skills_cli import SkillsCli
from engineering_influence.interactions.cli.tools_cli import ToolsCli
from engineering_influence.interfaces.bundle_fetcher_interface import BundleFetcherInterface
from engineering_influence.interfaces.mcp_remote_transport_factory_interface import (
    McpRemoteTransportFactoryInterface,
)
from engineering_influence.interfaces.model_probe_interface import ModelProbeInterface
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.interfaces.run_repository_interface import RunRepositoryInterface
from engineering_influence.interfaces.schema_migrator_interface import SchemaMigratorInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.tool_limits import ToolLimits
from engineering_influence.runtime.interfaces.cli_runtime_interface import CliRuntimeInterface
from engineering_influence.runtime.interfaces.publishing_controller_factory_interface import (
    PublishingControllerFactoryInterface,
)
from engineering_influence.runtime.serve_starter import ServeStarter
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface
from engineering_influence.services.interfaces.export_run_interface import ExportRunInterface
from engineering_influence.services.interfaces.model_doctor_interface import (
    ModelDoctorInterface,
)
from engineering_influence.services.interfaces.resume_run_interface import ResumeRunInterface
from engineering_influence.services.mcp_client_factory import McpClientFactory
from engineering_influence.services.mcp_server_probe import McpServerProbe
from engineering_influence.services.model_doctor import ModelDoctor
from engineering_influence.services.plugin_folder_converter import PluginFolderConverter
from engineering_influence.services.plugin_importer import PluginImporter
from engineering_influence.services.plugin_installer import PluginInstaller
from engineering_influence.services.plugin_lock_verifier import PluginLockVerifier
from engineering_influence.services.plugin_marketplace import PluginMarketplace
from engineering_influence.services.resume_run import ResumeRun
from engineering_influence.services.skill_converter import SkillConverter
from engineering_influence.services.skill_importer import SkillImporter
from engineering_influence.services.skill_lock_editor import SkillLockEditor
from engineering_influence.services.skill_lock_verifier import SkillLockVerifier
from engineering_influence.services.skill_markdown_parser import SkillMarkdownParser
from engineering_influence.services.start_pipeline import StartPipeline
from engineering_influence.services.tool_lock_auditor import ToolLockAuditor
from engineering_influence.services.tool_lock_editor import ToolLockEditor
from engineering_influence.services.tool_lock_verifier import ToolLockVerifier

if TYPE_CHECKING:
    import httpx

    from engineering_influence.controllers.publishing_controller import PublishingController


class CliRuntime(CliRuntimeInterface):
    """Wire ``ei``: a local pipeline planner, the book, server and database commands.

    ``probe_timeout_seconds`` bounds each request of ``doctor --probe``. ``publishing`` replaces the factory that wires the book commands to the real file system and
    toolchain, so a test can drive the whole command line over fakes.
    """

    TOOL_SESSION_SECONDS = 120.0
    TOOL_REQUEST_SECONDS = 30.0
    TOOL_MEMORY_BYTES = 2 * 1024**3
    TOOL_DISK_BYTES = 1024**3
    PLUGIN_BUNDLE_BYTES = 512 * 1024

    def __init__(
        self,
        publishing: PublishingControllerFactoryInterface | None = None,
        queue: QueueInterface | None = None,
        probe_timeout_seconds: float = 10.0,
        bundles: BundleFetcherInterface | None = None,
    ) -> None:
        self._publishing = publishing
        self._queue = queue
        self._probe_timeout_seconds = probe_timeout_seconds
        self._bundles = bundles

    def build(self) -> CliApplicationInterface:
        """Wire the controller, the book commands and the server commands."""
        controller = ProjectController(StartPipeline(InMemoryLedger(), InMemoryQueue()))
        return CliApplication(
            controller,
            BookCli(self._publishing_controller),
            ServeCli(ServeStarter()),
            DbCli(self._schema_migrator, self._secret_provider),
            RunCli(self._resume_run, self._cancel_run, self._run_status, self._export_run),
            DoctorCli(self._model_doctor, os.environ),
            self._tools_cli(),
            self._skills_cli(),
            self._plugins_cli(),
        )

    def _skills_cli(self) -> SkillsCli:
        """Wire ``skills``: it reads and writes the lock and the skill files, and starts nothing."""
        files = DirectorySkillFiles()
        parser = TomlSkillParser()
        verifier = SkillLockVerifier(files, parser)
        importer = SkillImporter(
            FileSkillSource(),
            SkillMarkdownParser(),
            SkillConverter(),
            TomlSkillWriter(),
            NewFileSkillSink(),
            DirectorySkillFiles.MAX_BYTES,
        )
        return SkillsCli(
            SkillLockEditor(files, parser, verifier),
            verifier,
            TomlSkillLockStore(),
            os.environ,
            importer,
        )

    def _plugins_cli(self) -> PluginsCli:
        """Wire ``plugins``: it reads and writes locks and files, and starts and contacts nothing.

        A bundle may be up to 512 KiB (a skill file stays at 64 KiB), which holds the most skills and
        servers a plugin may name.
        """
        skill_files = DirectorySkillFiles()
        skill_parser = TomlSkillParser()
        skills = SkillLockEditor(
            skill_files, skill_parser, SkillLockVerifier(skill_files, skill_parser)
        )
        bundle_files = DirectorySkillFiles(self.PLUGIN_BUNDLE_BYTES)
        parser = TomlPluginParser(skill_parser)
        fetcher = self._bundles or LazyBundleFetcher(self._bundle_fetcher)
        return PluginsCli(
            PluginInstaller(bundle_files, parser, TomlSkillWriter(), skills),
            PluginImporter(
                DirectoryPluginFolderReader(FileSkillSource()),
                PluginFolderConverter(SkillMarkdownParser(), SkillConverter()),
                TomlPluginWriter(),
                parser,
                NewFileSkillSink(),
                self.PLUGIN_BUNDLE_BYTES,
            ),
            PluginLockVerifier(bundle_files, parser),
            PluginMarketplace(
                fetcher,
                bundle_files,
                TomlPluginIndexParser(),
                parser,
                JsonMarketplaceParser(),
                self.PLUGIN_BUNDLE_BYTES,
            ),
            TomlPluginLockStore(),
            TomlSkillLockStore(),
            os.environ,
        )

    def _bundle_fetcher(self) -> BundleFetcherInterface:
        """The downloader for an index or a plugin file; it needs ``httpx``, so it is built on first use only."""
        import httpx

        from engineering_influence.infrastructure.plugins.http_bundle_fetcher import (
            HttpBundleFetcher,
        )
        from engineering_influence.infrastructure.security.public_https_url_pinner import (
            PublicHttpsUrlPinner,
        )
        from engineering_influence.infrastructure.security.public_https_url_policy import (
            PublicHttpsUrlPolicy,
        )

        client = httpx.Client(timeout=httpx.Timeout(self.TOOL_REQUEST_SECONDS, connect=10.0))
        return HttpBundleFetcher(
            client, PublicHttpsUrlPinner(PublicHttpsUrlPolicy()), self.TOOL_REQUEST_SECONDS
        )

    def _tools_cli(self) -> ToolsCli:
        """Wire ``tools``: a server is started only by ``add`` and ``verify``, under these limits.

        The limits are for one look at a server: two minutes, 2 GiB of memory and 1 GiB of disk.
        """
        limits = ToolLimits(
            timeout_seconds=self.TOOL_SESSION_SECONDS,
            max_memory_bytes=self.TOOL_MEMORY_BYTES,
            max_disk_bytes=self.TOOL_DISK_BYTES,
        )
        hasher = Sha256FileHasher()
        probe = McpServerProbe(
            StdioMcpTransportFactory(limits, os.environ),
            LazyRemoteTransportFactory(self._remote_transports),
            McpClientFactory("engineering-influence", __version__, self.TOOL_REQUEST_SECONDS),
            ToolLockVerifier(hasher),
        )
        return ToolsCli(
            ToolLockEditor(probe, hasher, PathExecutableFinder()),
            ToolLockAuditor(probe),
            TomlToolLockStore(),
            os.environ,
        )

    def _remote_transports(self) -> McpRemoteTransportFactoryInterface:
        """The transport for remote servers; it needs ``httpx``, so it is built on first use only."""
        from engineering_influence.infrastructure.security.public_https_url_pinner import (
            PublicHttpsUrlPinner,
        )
        from engineering_influence.infrastructure.security.public_https_url_policy import (
            PublicHttpsUrlPolicy,
        )
        from engineering_influence.infrastructure.tools.http_mcp_transport_factory import (
            HttpMcpTransportFactory,
        )

        return HttpMcpTransportFactory(
            self._tool_client,
            PublicHttpsUrlPinner(PublicHttpsUrlPolicy()),
            os.environ,
            self.TOOL_REQUEST_SECONDS,
            self.TOOL_SESSION_SECONDS,
        )

    def _tool_client(self) -> "httpx.Client":
        """A client for one look at a remote tool server; httpx is imported only when one is needed."""
        import httpx

        return httpx.Client(timeout=httpx.Timeout(self.TOOL_REQUEST_SECONDS, connect=10.0))

    def _model_doctor(self, probe: bool) -> ModelDoctorInterface:
        """Build the model doctor; the probe, and the HTTP client behind it, only if asked for.

        The probe's client times out after ``probe_timeout_seconds`` (ten by default) and lives
        until this one-shot command exits.
        """
        from engineering_influence.infrastructure.models.toml_model_catalog_loader import (
            TomlModelCatalogLoader,
        )
        from engineering_influence.infrastructure.models.toml_model_profile_loader import (
            TomlModelProfileLoader,
        )

        model_probe: ModelProbeInterface | None = None
        if probe:
            import httpx

            from engineering_influence.infrastructure.models.http_model_probe import (
                HttpModelProbe,
            )

            model_probe = HttpModelProbe(httpx.Client(timeout=self._probe_timeout_seconds))
        return ModelDoctor(
            TomlModelCatalogLoader(),
            TomlModelProfileLoader(),
            self._secret_provider(),
            model_probe,
            date.today(),
        )

    def _run_repository(self) -> RunRepositoryInterface:
        """Open the stack's run repository, after checking its schema is current."""
        from engineering_influence.repositories.sqlmodel_run_repository import (
            SqlModelRunRepository,
        )

        url = self._secret_provider().require("EI_DATABASE_URL")
        self._schema_migrator().check(url)
        # A one-shot command keeps no pool, so no connection outlives it.
        return SqlModelRunRepository(url, pooled=False)

    def _resume_run(self) -> ResumeRunInterface:
        """Build the resume service; it queues through the broker unless a queue was injected."""
        queue = self._queue
        if queue is None:
            import os

            from engineering_influence.infrastructure.rabbitmq_queue import RabbitMqQueueAdapter

            queue = RabbitMqQueueAdapter(
                self._secret_provider().require("EI_RABBITMQ_URL"),
                os.environ.get("EI_QUEUE_NAME", "engineering-influence.jobs"),
            )
        return ResumeRun(self._run_repository(), queue)

    def _run_status(self) -> RunControllerInterface:
        """Build the read controller; it needs only the database."""
        from engineering_influence.controllers.run_controller import RunController
        from engineering_influence.repositories.sqlmodel_artifact_store import (
            SqlModelArtifactStore,
        )
        from engineering_influence.repositories.sqlmodel_run_repository import (
            SqlModelRunRepository,
        )
        from engineering_influence.services.read_run import ReadRun

        url = self._secret_provider().require("EI_DATABASE_URL")
        self._schema_migrator().check(url)
        return RunController(
            ReadRun(
                SqlModelRunRepository(url, pooled=False),
                SqlModelArtifactStore(url, pooled=False),
            )
        )

    def _export_run(self) -> ExportRunInterface:
        """Build the export service; it reads the database and writes the folder it is given."""
        from engineering_influence.infrastructure.export.directory_project_files_writer import (
            DirectoryProjectFilesWriter,
        )
        from engineering_influence.repositories.sqlmodel_artifact_store import (
            SqlModelArtifactStore,
        )
        from engineering_influence.repositories.sqlmodel_run_repository import (
            SqlModelRunRepository,
        )
        from engineering_influence.services.export_run import ExportRun
        from engineering_influence.services.read_run import ReadRun

        url = self._secret_provider().require("EI_DATABASE_URL")
        self._schema_migrator().check(url)
        return ExportRun(
            ReadRun(
                SqlModelRunRepository(url, pooled=False),
                SqlModelArtifactStore(url, pooled=False),
            ),
            DirectoryProjectFilesWriter(),
        )

    def _cancel_run(self) -> CancelRunInterface:
        """Build the cancel service; it needs only the database."""
        return CancelRun(self._run_repository())

    def _secret_provider(self) -> SecretProviderInterface:
        """Build the secret provider on first use; it needs the ``runtime`` extra."""
        from engineering_influence.infrastructure.security.env_secret_provider import (
            EnvSecretProvider,
        )

        return EnvSecretProvider()

    def _schema_migrator(self) -> SchemaMigratorInterface:
        """Build the migrator on first use; it needs the ``runtime`` extra."""
        from engineering_influence.infrastructure.schema_migrator import SchemaMigrator

        return SchemaMigrator()

    def _publishing_controller(self, root: Path) -> "PublishingController":
        """Build the publishing controller on first use.

        The real factory imports Pillow, numpy and the PDF libraries, so it is imported only when
        a book command runs; the rest of ``ei`` keeps working without the ``publishing`` extra.
        """
        factory = self._publishing
        if factory is None:
            from engineering_influence.runtime.publishing_controller_factory import (
                PublishingControllerFactory,
            )

            factory = PublishingControllerFactory()
        return factory.create(root)
