# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Load settings and start the API or the worker."""

from collections.abc import Callable

from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.interfaces.serve_starter_interface import ServeStarterInterface
from engineering_influence.runtime.app_settings import AppSettings

Runner = Callable[[AppSettings, SecretProviderInterface], None]


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
    ) -> None:
        self._secrets = secrets
        self._run_api = run_api
        self._run_worker = run_worker

    def start(self, target: str) -> None:
        """Run ``api`` or ``worker`` until it stops."""
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
        else:
            (self._run_worker or self._default_worker)(settings, secrets)

    @staticmethod
    def _default_api(settings: AppSettings, secrets: SecretProviderInterface) -> None:
        from engineering_influence.runtime.api_runtime import ApiRuntime

        ApiRuntime(settings, secrets).run()

    @staticmethod
    def _default_worker(settings: AppSettings, secrets: SecretProviderInterface) -> None:
        from engineering_influence.runtime.worker_runtime import WorkerRuntime

        WorkerRuntime(settings).run()
