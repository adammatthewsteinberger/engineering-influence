# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A plugin that was just installed: the two locks as they now stand, and what was installed."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.plugin_addition_interface import (
    PluginAdditionInterface,
)
from engineering_influence.models.plugin_bundle import PluginBundle
from engineering_influence.models.plugin_lock import PluginLock
from engineering_influence.models.skill_lock import SkillLock


@dataclass(frozen=True, slots=True)
class PluginAddition(PluginAdditionInterface):
    """The new plugin lock, the new skill lock (its skills added, each enabled for no stage) and the bundle."""

    lock: PluginLock
    skills: SkillLock
    bundle: PluginBundle
