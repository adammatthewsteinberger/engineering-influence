# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A plugin that was just removed, and what was left in place."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.plugin_removal_interface import (
    PluginRemovalInterface,
)
from engineering_influence.models.plugin_lock import PluginLock
from engineering_influence.models.skill_lock import SkillLock


@dataclass(frozen=True, slots=True)
class PluginRemoval(PluginRemovalInterface):
    """The two locks as they now stand, the skills taken out, and those left because they had changed.

    A skill is taken out only if it is still exactly what the plugin installed. One that was locked
    again with different text since belongs to the person now and is left, and named.
    """

    lock: PluginLock
    skills: SkillLock
    removed: tuple[str, ...]
    kept: tuple[str, ...]
