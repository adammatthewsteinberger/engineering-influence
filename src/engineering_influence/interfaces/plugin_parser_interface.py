# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: turning a plugin file's bytes into a plugin."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.plugin import Plugin


class PluginParserInterface(ABC):
    """Reads a plugin, strictly, from the bytes of its file."""

    __slots__ = ()

    @abstractmethod
    def parse(self, data: bytes, name: str) -> Plugin:
        """The plugin, or an ApplicationError (PLUGIN_INVALID) saying why the file is not one.

        ``name`` is what the file is called without its extension; the file must name itself the same.
        """
