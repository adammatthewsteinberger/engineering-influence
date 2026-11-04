# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Constant-time API key verification that fails closed."""

from collections.abc import Iterable

from vibey_bootstrap.security import compare_secrets

from engineering_influence.interfaces.api_key_verifier_port import ApiKeyVerifierPort
from engineering_influence.interfaces.secret_provider_port import SecretProviderPort

MINIMUM_KEY_LENGTH = 24


class ConstantTimeApiKeyVerifier(ApiKeyVerifierPort):
    """Accept only keys from an explicit, non-empty, strong set.

    vibey_bootstrap's own ``verify_api_key_header`` passes every request when its
    variable is unset. This adapter reuses only its constant-time comparison so an
    absent configuration can never open the API.
    """

    def __init__(self, keys: Iterable[str]) -> None:
        cleaned = tuple(key.strip() for key in keys if key.strip())
        if not cleaned:
            raise ValueError("at least one API key is required")
        if any(len(key) < MINIMUM_KEY_LENGTH for key in cleaned):
            raise ValueError(f"API keys must be at least {MINIMUM_KEY_LENGTH} characters")
        self._keys = cleaned

    @classmethod
    def from_secrets(
        cls, secrets: SecretProviderPort, name: str = "EI_API_KEYS"
    ) -> "ConstantTimeApiKeyVerifier":
        """Build from a comma-separated secret, failing when it is not configured."""
        return cls(secrets.require(name).split(","))

    def verify(self, presented: str | None) -> bool:
        """Compare against every key so timing does not reveal which one matched."""
        if not presented:
            return False
        matched = False
        for key in self._keys:
            matched = compare_secrets(presented, key) or matched
        return matched
