# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Chooses what does a run's stages: the offline placeholder, or a model, only when told to."""

from collections.abc import Mapping
from datetime import date
from pathlib import Path

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.deterministic_stage_executor import (
    DeterministicStageExecutor,
)
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
from engineering_influence.infrastructure.research.brave_search_provider import (
    BraveSearchProvider,
)
from engineering_influence.infrastructure.research.html_text_extractor import HtmlTextExtractor
from engineering_influence.infrastructure.research.http_source_fetcher import HttpSourceFetcher
from engineering_influence.infrastructure.research.searxng_search_provider import (
    SearxngSearchProvider,
)
from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.interfaces.model_interface import ModelInterface
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.model_profile import ModelProfile
from engineering_influence.models.provider_descriptor import ProviderDescriptor
from engineering_influence.models.tool_loop_limits import ToolLoopLimits
from engineering_influence.runtime.interfaces.stage_executor_runtime_interface import (
    StageExecutorRuntimeInterface,
)
from engineering_influence.services.ask_model import AskModel
from engineering_influence.services.call_model import CallModel
from engineering_influence.services.fallback_search_provider import FallbackSearchProvider
from engineering_influence.services.fetch_url_tool import FetchUrlTool
from engineering_influence.services.model_stage_executor import ModelStageExecutor
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.run_tool_loop import RunToolLoop
from engineering_influence.services.spend_guard import SpendGuard
from engineering_influence.services.tool_registry import ToolRegistry
from engineering_influence.services.tool_runner import ToolRunner
from engineering_influence.services.web_search_tool import WebSearchTool


class StageExecutorRuntime(StageExecutorRuntimeInterface):
    """``EI_STAGE_EXECUTOR`` picks ``deterministic`` (the default) or ``model``.

    ``model`` spends money, so it is never inferred from a profile file being there. It needs
    ``EI_STAGE_MODEL_PROFILE`` (the profile's name), ``EI_MODEL_PROFILES`` and ``EI_MODEL_CATALOG``
    (the files ``ei doctor --models`` checks), the profile's key, and a web search for the
    research stage: ``EI_SEARXNG_URL`` (a SearXNG instance, tried first), ``BRAVE_SEARCH_API_KEY``
    (Brave, the backup, or the only search when there is no instance), or both. Anything missing, an unknown
    profile, no price in force today, or a key that would cross a network in clear stops the
    process at start, before any call is made. The price is looked up once, at start.
    """

    CONNECT_TIMEOUT_SECONDS = 10.0
    RESEARCH_TIMEOUT_SECONDS = 30.0

    def __init__(
        self,
        environment: Mapping[str, str],
        secrets: SecretProviderInterface,
        today: date,
        request_timeout_seconds: float = 600.0,
    ) -> None:
        self._environment = environment
        self._secrets = secrets
        self._today = today
        self._timeout = request_timeout_seconds
        self._client: httpx.Client | None = None
        self._research_client: httpx.Client | None = None
        self._runner: ToolRunner | None = None

    def build(
        self, artifacts: ArtifactStoreInterface, journal: JournalInterface
    ) -> StageExecutorInterface:
        """The offline placeholder, or a model-backed executor when the environment opts in."""
        kind = self._environment.get("EI_STAGE_EXECUTOR", "deterministic")
        if kind == "deterministic":
            return DeterministicStageExecutor(artifacts, journal)
        if kind != "model":
            raise ApplicationError(
                code="STAGE_EXECUTOR_UNKNOWN",
                message=f"EI_STAGE_EXECUTOR is {kind!r}; use 'deterministic' or 'model'",
                http_status=503,
            )
        model = self._model()
        tools = ToolRegistry(self._tools())
        limits = ToolLoopLimits()
        runner = ToolRunner(tools, journal, limits)
        self._runner = runner
        ask = AskModel(CallModel(model, journal), model)
        return ModelStageExecutor(
            NonfictionRecipes(),
            TomlPromptLibrary(),
            artifacts,
            RunToolLoop(ask, runner, limits),
            tools,
            SpendGuard,
        )

    def close(self) -> None:
        """Close the HTTP client and the tool threads behind a model-backed executor, if built."""
        if self._runner is not None:
            self._runner.close()
            self._runner = None
        for client in (self._client, self._research_client):
            if client is not None:
                client.close()
        self._client = None
        self._research_client = None

    def _tools(self) -> tuple[ToolInterface, ...]:
        """Search and page reading, which the research stage names."""
        client = httpx.Client(
            timeout=httpx.Timeout(
                self.RESEARCH_TIMEOUT_SECONDS, connect=self.CONNECT_TIMEOUT_SECONDS
            )
        )
        self._research_client = client
        fetcher = HttpSourceFetcher(client, PublicHttpsUrlPolicy(), HtmlTextExtractor())
        return (WebSearchTool(self._search(client)), FetchUrlTool(fetcher))

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
