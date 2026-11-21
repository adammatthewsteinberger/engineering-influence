# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How to reach one model: the adapter, the server, and the name of the variable holding its key."""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from engineering_influence.models.interfaces.model_profile_interface import (
    ModelProfileInterface,
)

ADAPTERS = ("anthropic", "openai_compatible")
OUTPUT_CAP_FIELDS = ("max_tokens", "max_completion_tokens")
LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")
ENV_NAME = re.compile(r"[A-Z_][A-Z0-9_]*")


@dataclass(frozen=True, slots=True)
class ModelProfile(ModelProfileInterface):
    """A named way to reach a model, whether a hosted API or a server on this machine.

    ``api_key_env`` is the NAME of an environment variable, never the key: a value that is not
    shaped like a variable name is refused, without being repeated, so a pasted key cannot be
    saved in a file that gets committed. It may be blank only for an OpenAI-compatible server,
    which is how a local model is described. ``provider`` and ``model`` pick the price in the
    catalog.
    """

    name: str
    adapter: str
    provider: str
    model: str
    base_url: str
    api_key_env: str = ""
    output_cap_field: str = "max_tokens"

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.provider.strip() or not self.model.strip():
            raise ValueError("a profile needs a name, a provider and a model")
        if self.adapter not in ADAPTERS:
            raise ValueError(f"adapter must be one of {', '.join(ADAPTERS)}")
        if self.output_cap_field not in OUTPUT_CAP_FIELDS:
            raise ValueError(f"output_cap_field must be one of {', '.join(OUTPUT_CAP_FIELDS)}")
        parts = urlsplit(self.base_url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError("base_url must be an http or https URL with a host")
        if parts.username is not None or parts.password is not None:
            raise ValueError("base_url must not carry a user name or password")
        if self.api_key_env and not ENV_NAME.fullmatch(self.api_key_env):
            raise ValueError(
                "api_key_env must be the NAME of an environment variable, such as "
                "ANTHROPIC_API_KEY, not the key itself"
            )
        if self.adapter == "anthropic" and not self.api_key_env:
            raise ValueError("an anthropic profile needs api_key_env")

    def requires_key(self) -> bool:
        """A key is required exactly when a variable is named for it."""
        return bool(self.api_key_env)

    def sends_key_in_clear(self) -> bool:
        """True for a key, plain http, and a host that is not loopback."""
        parts = urlsplit(self.base_url)
        return (
            self.requires_key()
            and parts.scheme == "http"
            and (parts.hostname or "") not in LOOPBACK_HOSTS
        )
