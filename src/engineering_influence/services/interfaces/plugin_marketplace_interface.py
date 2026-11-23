# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginMarketplace."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.marketplace_listing import MarketplaceListing
    from engineering_influence.models.plugin_download import PluginDownload
    from engineering_influence.models.plugin_index import PluginIndex


class PluginMarketplaceInterface(ABC):
    """Reads a marketplace index and downloads a plugin file from it, checking the hash before anything else."""

    __slots__ = ()

    @abstractmethod
    def index(self, address: str) -> PluginIndex:
        """The index at a file path or an https address, or an ApplicationError saying why it is not usable."""

    @abstractmethod
    def listing(self, address: str) -> MarketplaceListing:
        """The Claude Code marketplace at a file path or an https address as a list, or an ApplicationError."""

    @abstractmethod
    def download(self, address: str, name: str, folder: Path) -> PluginDownload:
        """Download the named plugin to ``folder``, checked against the index's hash; nothing is installed."""
