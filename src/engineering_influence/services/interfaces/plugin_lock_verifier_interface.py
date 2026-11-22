# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginLockVerifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.plugin_lock import PluginLock
    from engineering_influence.models.skill_lock import SkillLock


class PluginLockVerifierInterface(ABC):
    """Checks that each installed plugin is still the bundle a person reviewed."""

    __slots__ = ()

    @abstractmethod
    def problems(self, plugins: PluginLock, skills: SkillLock, folder: Path) -> tuple[str, ...]:
        """What no longer matches, for every installed plugin, in name order."""
