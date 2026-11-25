# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginIndex."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.plugin_index_entry import PluginIndexEntry


class PluginIndexInterface(ABC):
    """A marketplace index: a list of plugin files, each with an address and a hash."""

    __slots__ = ()

    @abstractmethod
    def find(self, name: str) -> PluginIndexEntry | None:
        """The entry with this name, or None."""

    @abstractmethod
    def search(self, text: str) -> tuple[PluginIndexEntry, ...]:
        """The entries whose name or description contains the text, ignoring case; all of them for no text."""
