# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Load settings and start the API or the worker."""

from collections.abc import Callable

from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.interfaces.serve_starter_interface import ServeStarterInterface
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.interfaces.api_runtime_interface import ApiRuntimeInterface
from engineering_influence.runtime.interfaces.mcp_runtime_interface import McpRuntimeInterface
from engineering_influence.runtime.interfaces.worker_runtime_interface import WorkerRuntimeInterface

Runner = Callable[[AppSettings, SecretProviderInterface], None]
ApiRuntimeFactory = Callable[[AppSettings, SecretProviderInterface], ApiRuntimeInterface]
WorkerRuntimeFactory = Callable[[AppSettings], WorkerRuntimeInterface]
McpRuntimeFactory = Callable[[AppSettings], McpRuntimeInterface]


class ServeStarter(ServeStarterInterface):
    """Compose the settings, secrets and runtime for one ``serve`` target.

    The runtimes and their libraries are imported only when a target starts, so an install
    without the ``api`` and ``runtime`` extras can still import the CLI and fails with an
    ``ImportError`` that the CLI reports.
    """

    def __init__(
        self,
        secrets: SecretProviderInterface | None = None,
        run_api: Runner | None = None,
        run_worker: Runner | None = None,
        api_runtime: ApiRuntimeFactory | None = None,
        worker_runtime: WorkerRuntimeFactory | None = None,
        mcp_runtime: McpRuntimeFactory | None = None,
    ) -> None:
        """Remember the secrets, the runners and the API runtime factory for each serve target."""
        self._secrets = secrets
        self._run_api = run_api
        self._run_worker = run_worker
        self._api_runtime = api_runtime
        self._worker_runtime = worker_runtime
        self._mcp_runtime = mcp_runtime

    def start(self, target: str) -> None:
        """Run ``api``, ``worker`` or ``mcp`` until it stops."""
        from engineering_influence.infrastructure.security.env_secret_provider import (
            EnvSecretProvider,
        )
        from engineering_influence.runtime.environment_settings_loader import (
            EnvironmentSettingsLoader,
        )

        secrets = self._secrets or EnvSecretProvider()
        settings = EnvironmentSettingsLoader(secrets).load()
        if target == "api":
            (self._run_api or self._default_api)(settings, secrets)
        elif target == "mcp":
            (self._mcp_runtime or self._real_mcp)(settings).run()
        else:
            (self._run_worker or self._default_worker)(settings, secrets)

    def _default_api(self, settings: AppSettings, secrets: SecretProviderInterface) -> None:
        (self._api_runtime or self._real_api)(settings, secrets).run()

    def _default_worker(self, settings: AppSettings, secrets: SecretProviderInterface) -> None:
        (self._worker_runtime or self._real_worker)(settings).run()

    @staticmethod
    def _real_api(settings: AppSettings, secrets: SecretProviderInterface) -> ApiRuntimeInterface:
        from engineering_influence.runtime.api_runtime import ApiRuntime

        return ApiRuntime(settings, secrets)

    @staticmethod
    def _real_mcp(settings: AppSettings) -> McpRuntimeInterface:
        from engineering_influence.runtime.mcp_runtime import McpRuntime

        return McpRuntime(settings)

    @staticmethod
    def _real_worker(settings: AppSettings) -> WorkerRuntimeInterface:
        from engineering_influence.runtime.worker_runtime import WorkerRuntime

        return WorkerRuntime(settings)
