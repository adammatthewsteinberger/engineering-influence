# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Read a model catalog from a TOML file the deployment owns."""

import tomllib
from pathlib import Path
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.model_catalog_loader_interface import (
    ModelCatalogLoaderInterface,
)
from engineering_influence.models.model_catalog import ModelCatalog
from engineering_influence.models.provider_descriptor import ProviderDescriptor


class TomlModelCatalogLoader(ModelCatalogLoaderInterface):
    """Expand each `[[model]]` and its `[[model.price]]` entries into one descriptor per price.

    Prices are whole micro-dollars per million tokens (`input`, `output`, `cache_read`,
    `cache_write`), never decimals, so nothing is rounded on the way in. The file is the
    deployment's, not the package's: prices change, and the package cannot vouch for them.
    """

    def load(self, path: Path) -> ModelCatalog:
        """Parse the catalog at ``path``; any problem is reported with the entry it is in."""
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise self._invalid(f"cannot read {path}: {error.strerror}") from error
        except tomllib.TOMLDecodeError as error:
            raise self._invalid(f"{path} is not valid TOML: {error}") from error
        descriptors: list[ProviderDescriptor] = []
        for index, entry in enumerate(data.get("model", [])):
            descriptors.extend(self._expand(entry, index))
        try:
            return ModelCatalog(tuple(descriptors))
        except ValueError as error:
            raise self._invalid(str(error)) from error

    def _expand(self, entry: dict[str, Any], index: int) -> list[ProviderDescriptor]:
        where = f"model #{index + 1} ({entry.get('provider', '?')}/{entry.get('model', '?')})"
        prices = entry.get("price", [])
        if not prices:
            raise self._invalid(f"{where} has no [[model.price]] entry")
        try:
            return [
                ProviderDescriptor(
                    provider=entry["provider"],
                    model=entry["model"],
                    family=entry["family"],
                    context_window=entry["context_window"],
                    max_output_tokens=entry["max_output_tokens"],
                    input_micro_usd_per_mtok=price["input"],
                    output_micro_usd_per_mtok=price["output"],
                    cache_read_micro_usd_per_mtok=price["cache_read"],
                    cache_write_micro_usd_per_mtok=price["cache_write"],
                    batch_discount_percent=price["batch_discount_percent"],
                    price_effective=price["effective"],
                    usage_policy_url=entry["usage_policy_url"],
                    long_context_threshold_tokens=price.get("long_context_threshold_tokens", 0),
                    long_context_input_percent=price.get("long_context_input_percent", 100),
                    long_context_output_percent=price.get("long_context_output_percent", 100),
                )
                for price in prices
            ]
        except KeyError as error:
            raise self._invalid(f"{where} is missing {error.args[0]!r}") from error
        except (TypeError, ValueError, AttributeError) as error:
            raise self._invalid(f"{where}: {error}") from error

    @staticmethod
    def _invalid(message: str) -> ApplicationError:
        return ApplicationError(code="MODEL_CATALOG_INVALID", message=message, http_status=503)
