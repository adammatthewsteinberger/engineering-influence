# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A plugin file that has been read: what it says, and the hash of exactly the bytes that said it."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.plugin_bundle_interface import PluginBundleInterface
from engineering_influence.models.plugin import Plugin


@dataclass(frozen=True, slots=True)
class PluginBundle(PluginBundleInterface):
    """The plugin and the SHA-256 of the bytes it was read from, for a person to review before installing."""

    plugin: Plugin
    sha256: str
