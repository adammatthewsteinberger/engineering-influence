# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ModelCatalog."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from engineering_influence.models.provider_descriptor import ProviderDescriptor


class ModelCatalogInterface(ABC):
    """The models a deployment may call, with every price they have had and when it took effect."""

    __slots__ = ()

    @abstractmethod
    def descriptor(self, provider: str, model: str, on: date) -> ProviderDescriptor:
        """The descriptor whose prices were in force on the date, or an ApplicationError."""
