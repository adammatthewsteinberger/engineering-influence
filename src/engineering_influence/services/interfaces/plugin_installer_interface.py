# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginInstaller."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.plugin_addition import PluginAddition
    from engineering_influence.models.plugin_bundle import PluginBundle
    from engineering_influence.models.plugin_lock import PluginLock
    from engineering_influence.models.plugin_removal import PluginRemoval
    from engineering_influence.models.skill_lock import SkillLock


class PluginInstallerInterface(ABC):
    """Installs a plugin by locking its skills and recording its hash, and runs and contacts nothing."""

    __slots__ = ()

    @abstractmethod
    def inspect(self, source: Path) -> PluginBundle:
        """Read and check a plugin file and change nothing."""

    @abstractmethod
    def add(
        self,
        plugins: PluginLock,
        skills: SkillLock,
        plugin_folder: Path,
        skill_folder: Path,
        source: Path,
    ) -> PluginAddition:
        """Install the plugin in ``source``: lock its skills, keep a copy, record its hash."""

    @abstractmethod
    def remove(
        self,
        plugins: PluginLock,
        skills: SkillLock,
        plugin_folder: Path,
        skill_folder: Path,
        name: str,
    ) -> PluginRemoval:
        """Take the plugin out, with the skills it installed that are still exactly what it installed."""
