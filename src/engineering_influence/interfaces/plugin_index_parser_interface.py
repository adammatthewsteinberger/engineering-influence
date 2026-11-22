# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: turning a marketplace index file's bytes into an index."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.plugin_index import PluginIndex


class PluginIndexParserInterface(ABC):
    """Reads a marketplace index, strictly, from the bytes of its file."""

    __slots__ = ()

    @abstractmethod
    def parse(self, data: bytes) -> PluginIndex:
        """The index, or an ApplicationError (PLUGIN_INDEX_INVALID) saying why the file is not one."""
