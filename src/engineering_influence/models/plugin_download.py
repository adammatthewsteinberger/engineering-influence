# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A plugin file that was downloaded and checked: which entry, what it says, and where it was saved."""

from dataclasses import dataclass
from pathlib import Path

from engineering_influence.models.interfaces.plugin_download_interface import (
    PluginDownloadInterface,
)
from engineering_influence.models.plugin_bundle import PluginBundle
from engineering_influence.models.plugin_index_entry import PluginIndexEntry


@dataclass(frozen=True, slots=True)
class PluginDownload(PluginDownloadInterface):
    """The index entry, the bundle (read only after its hash matched the entry's) and the saved file.

    Nothing is installed: this is a file on disk that a person can read with ``ei plugins show`` and
    install with ``ei plugins add``.
    """

    entry: PluginIndexEntry
    bundle: PluginBundle
    path: Path
