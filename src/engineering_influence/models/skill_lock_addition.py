# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A skill that was just locked, and the lock that now holds it."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.skill_lock_addition_interface import (
    SkillLockAdditionInterface,
)
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_lock import SkillLock


@dataclass(frozen=True, slots=True)
class SkillLockAddition(SkillLockAdditionInterface):
    """The new lock and the skill that was added to it, for a person to review."""

    lock: SkillLock
    skill: Skill
