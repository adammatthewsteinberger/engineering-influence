# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ArtifactStoreFactory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.runtime.app_settings import AppSettings


class ArtifactStoreFactoryInterface(ABC):
    """Chooses where a run's files are kept, from the settings."""

    __slots__ = ()

    @abstractmethod
    def build(self, settings: AppSettings) -> object:
        """The artifact store the settings name."""
