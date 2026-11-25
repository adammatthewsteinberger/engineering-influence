# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginFolderConverter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.plugin_conversion import PluginConversion
    from engineering_influence.models.plugin_folder import PluginFolder


class PluginFolderConverterInterface(ABC):
    """Turns a plugin folder into a bundle, leaving out and naming what a bundle cannot hold."""

    __slots__ = ()

    @abstractmethod
    def convert(self, folder: PluginFolder, name: str | None, version: int) -> PluginConversion:
        """The bundle and what was skipped, or an ApplicationError when nothing could be carried over."""
