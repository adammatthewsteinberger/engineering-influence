# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: writing a plugin as the bytes of its file."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.plugin import Plugin


class PluginWriterInterface(ABC):
    """Renders a plugin as a bundle file, the same bytes every time."""

    __slots__ = ()

    @abstractmethod
    def render(self, plugin: Plugin) -> bytes:
        """The bundle's bytes, which the plugin parser reads back as this plugin."""
