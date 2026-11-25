# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EnvironmentSettingsLoader."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.runtime.app_settings import AppSettings


class EnvironmentSettingsLoaderInterface(ABC):
    """``EI_DATABASE_URL`` and ``EI_RABBITMQ_URL`` are required; the rest have safe defaults."""

    __slots__ = ()

    @abstractmethod
    def load(self) -> AppSettings:
        """Return validated settings or raise with the name of the offending variable."""
