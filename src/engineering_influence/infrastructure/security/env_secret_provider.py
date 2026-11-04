# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fail-closed secrets read from the process environment."""

from vibey_bootstrap.failclose import ConfigurationError, require_env

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.secret_provider_port import SecretProviderPort


class EnvSecretProvider(SecretProviderPort):
    """Read a secret from the environment and stop when it is absent or blank."""

    def require(self, name: str) -> str:
        """Return the secret; never fall back to a default value."""
        try:
            return require_env(name)
        except ConfigurationError as error:
            raise ApplicationError(
                code="SECRET_MISSING",
                message=f"required secret {name} is not configured",
                http_status=503,
            ) from error
