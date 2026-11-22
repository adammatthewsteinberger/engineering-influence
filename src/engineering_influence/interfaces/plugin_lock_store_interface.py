# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: where the plugin lock is kept."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.plugin_lock import PluginLock


class PluginLockStoreInterface(ABC):
    """Reads and writes the plugin lock file."""

    __slots__ = ()

    @abstractmethod
    def load(self, path: Path) -> PluginLock | None:
        """The lock at ``path``, or None when there is no file; an ApplicationError when it is unusable."""

    @abstractmethod
    def save(self, path: Path, lock: PluginLock) -> None:
        """Write the lock, replacing the file whole or not at all."""
