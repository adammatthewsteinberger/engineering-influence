# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Model probe port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.model_availability import ModelAvailability
    from engineering_influence.models.model_profile import ModelProfile


class ModelProbeInterface(ABC):
    """Ask a model server whether it accepts this key, without asking the model anything."""

    __slots__ = ()

    @abstractmethod
    def probe(self, profile: ModelProfile, api_key: str) -> ModelAvailability:
        """What the server says about the key; raise an ApplicationError if it cannot be reached."""
