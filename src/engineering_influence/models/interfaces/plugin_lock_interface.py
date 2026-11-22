# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginLock."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.plugin_lock import PluginLock
    from engineering_influence.models.plugin_lock_entry import PluginLockEntry


class PluginLockInterface(ABC):
    """The plugins a person has installed, as written in the plugin lock file."""

    __slots__ = ()

    @abstractmethod
    def entry(self, name: str) -> PluginLockEntry | None:
        """The locked plugin with this name, or None."""

    @abstractmethod
    def with_entry(self, entry: PluginLockEntry) -> PluginLock:
        """This lock with the entry added; a plugin that is already installed is not replaced."""

    @abstractmethod
    def without(self, name: str) -> PluginLock:
        """This lock with the plugin taken out."""

    @abstractmethod
    def names(self) -> tuple[str, ...]:
        """The installed plugins' names, sorted."""
