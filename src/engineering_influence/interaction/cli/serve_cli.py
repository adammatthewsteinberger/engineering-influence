# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``serve`` command group: run the API or the worker."""

import argparse
import sys
from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.secret_provider_port import SecretProviderPort
from engineering_influence.runtime.app_settings import AppSettings

Runner = Callable[[AppSettings, SecretProviderPort], None]


class ServeCli:
    """Start a long-running process from environment settings.

    A configuration problem prints which variable is wrong and exits 2. It never prints a
    traceback, which could carry a connection string.
    """

    def __init__(
        self,
        secrets: SecretProviderPort | None = None,
        run_api: Runner | None = None,
        run_worker: Runner | None = None,
    ) -> None:
        self._secrets = secrets
        self._run_api = run_api
        self._run_worker = run_worker

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``serve api`` and ``serve worker``."""
        serve = subparsers.add_parser("serve", help="run the API or the worker")
        serve.add_argument("target", choices=("api", "worker"))

    def run(self, arguments: argparse.Namespace) -> int:
        """Load settings, then run the chosen process; return its exit status."""
        try:
            from engineering_influence.infrastructure.security.env_secret_provider import (
                EnvSecretProvider,
            )
            from engineering_influence.runtime.environment_settings_loader import (
                EnvironmentSettingsLoader,
            )

            secrets = self._secrets or EnvSecretProvider()
            settings = EnvironmentSettingsLoader(secrets).load()
            if arguments.target == "api":
                (self._run_api or self._default_api)(settings, secrets)
            else:
                (self._run_worker or self._default_worker)(settings, secrets)
        except ImportError as error:
            print(
                "error: serve needs the api and runtime extras: "
                f"pip install 'engineering-influence[api,runtime]' ({error.name} is missing)",
                file=sys.stderr,
            )
            return 1
        except (ApplicationError, ValueError) as error:
            message = error.message if isinstance(error, ApplicationError) else str(error)
            print(f"error: {message}", file=sys.stderr)
            return 2
        return 0

    @staticmethod
    def _default_api(settings: AppSettings, secrets: SecretProviderPort) -> None:
        from engineering_influence.runtime.api_runtime import ApiRuntime

        ApiRuntime(settings, secrets).run()

    @staticmethod
    def _default_worker(settings: AppSettings, secrets: SecretProviderPort) -> None:
        from engineering_influence.runtime.worker_runtime import WorkerRuntime

        WorkerRuntime(settings).run()
