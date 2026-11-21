# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Read model profiles from a TOML file the deployment owns."""

import tomllib
from pathlib import Path
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.model_profile_loader_interface import (
    ModelProfileLoaderInterface,
)
from engineering_influence.models.model_profile import ModelProfile

KEYS = frozenset(
    {"name", "adapter", "provider", "model", "base_url", "api_key_env", "output_cap_field"}
)
DEFAULT_BASE_URLS = {"anthropic": "https://api.anthropic.com"}


class TomlModelProfileLoader(ModelProfileLoaderInterface):
    """Expand each ``[[profile]]`` into a ``ModelProfile``.

    An unknown key is refused rather than ignored: a misspelt ``api_key_env`` would otherwise
    leave the key blank and the profile would quietly call a server with no credentials.
    ``base_url`` may be left out only for ``anthropic``; a server you run yourself must say
    where it is.
    """

    def load(self, path: Path) -> tuple[ModelProfile, ...]:
        """Parse the profiles at ``path``; any problem is reported with the entry it is in."""
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise self._invalid(f"cannot read {path}: {error.strerror}") from error
        except tomllib.TOMLDecodeError as error:
            raise self._invalid(f"{path} is not valid TOML: {error}") from error
        unknown = sorted(set(data) - {"profile"})
        if unknown:
            raise self._invalid(f"{path} has an unknown top-level key {unknown[0]!r}")
        entries = data.get("profile", [])
        if not entries:
            raise self._invalid(f"{path} has no [[profile]] entry")
        profiles = tuple(self._expand(entry, index) for index, entry in enumerate(entries))
        names = [profile.name for profile in profiles]
        if len(set(names)) != len(names):
            raise self._invalid("two profiles share a name; each must be unique")
        return profiles

    def _expand(self, entry: dict[str, Any], index: int) -> ModelProfile:
        where = f"profile #{index + 1} ({entry.get('name', '?')})"
        unknown = sorted(set(entry) - KEYS)
        if unknown:
            raise self._invalid(f"{where} has an unknown key {unknown[0]!r}")
        fields = dict(entry)
        default_url = DEFAULT_BASE_URLS.get(str(entry.get("adapter")))
        if default_url is not None:
            fields.setdefault("base_url", default_url)
        try:
            return ModelProfile(**fields)
        except TypeError as error:
            # Unknown keys were refused above, so a TypeError can only be a missing required key.
            missing = sorted({"name", "adapter", "provider", "model", "base_url"} - set(fields))
            raise self._invalid(f"{where} is missing {missing[0]!r}") from error
        except (ValueError, AttributeError) as error:
            raise self._invalid(f"{where}: {error}") from error

    @staticmethod
    def _invalid(message: str) -> ApplicationError:
        return ApplicationError(code="MODEL_PROFILE_INVALID", message=message, http_status=503)
