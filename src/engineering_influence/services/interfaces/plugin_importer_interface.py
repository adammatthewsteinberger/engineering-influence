# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginImporter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.plugin_import_result import PluginImportResult


class PluginImporterInterface(ABC):
    """Reads a Claude Code plugin folder and writes a bundle file for review; it installs and starts nothing."""

    __slots__ = ()

    @abstractmethod
    def import_plugin(
        self, source: Path, name: str | None, version: int, target: Path | None
    ) -> PluginImportResult:
        """Write the bundle and say what it holds, or raise an ApplicationError saying what to change."""
