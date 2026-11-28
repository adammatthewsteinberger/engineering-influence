# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The models a deployment may call, with every price they have had and when it took effect."""

from dataclasses import dataclass
from datetime import date

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.interfaces.model_catalog_interface import (
    ModelCatalogInterface,
)
from engineering_influence.models.provider_descriptor import ProviderDescriptor


@dataclass(frozen=True, slots=True)
class ModelCatalog(ModelCatalogInterface):
    """Descriptors keyed by provider, model and the date their prices take effect.

    A model with no price in force on a date is refused, never guessed: a run that cannot price
    a call cannot reserve for it, so it must not make it.
    """

    descriptors: tuple[ProviderDescriptor, ...]

    def __post_init__(self) -> None:
        """Validate the descriptors keyed by provider, model and date when the catalog is built."""
        keys = [(d.provider, d.model, d.price_effective) for d in self.descriptors]
        if len(set(keys)) != len(keys):
            raise ValueError("a model cannot have two prices with the same effective date")

    def descriptor(self, provider: str, model: str, on: date) -> ProviderDescriptor:
        """The descriptor whose prices were in force on ``on``: the latest one effective by then."""
        in_force = [
            d
            for d in self.descriptors
            if d.provider == provider and d.model == model and d.price_effective <= on.isoformat()
        ]
        if not in_force:
            raise ApplicationError(
                code="MODEL_UNPRICED",
                message=(
                    f"no price for {provider}/{model} in force on {on.isoformat()}: add an entry "
                    "effective on or before that date to the model catalog"
                ),
                http_status=503,
            )
        return max(in_force, key=lambda d: d.price_effective)
