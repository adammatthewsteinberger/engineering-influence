# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: where a Claude Code plugin folder is read from."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.plugin_folder import PluginFolder


class PluginFolderReaderInterface(ABC):
    """Reads a plugin folder's manifest, MCP servers and skills, and nothing else."""

    __slots__ = ()

    @abstractmethod
    def read(self, path: Path) -> PluginFolder:
        """The folder's contents, or an ApplicationError (PLUGIN_FOLDER_INVALID) saying why it cannot be read."""
