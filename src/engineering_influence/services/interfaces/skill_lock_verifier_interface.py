# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SkillLockVerifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.skill import Skill
    from engineering_influence.models.skill_lock import SkillLock
    from engineering_influence.models.skill_lock_entry import SkillLockEntry


class SkillLockVerifierInterface(ABC):
    """Checks that each installed skill is still the text a person locked."""

    __slots__ = ()

    @abstractmethod
    def skill(self, entry: SkillLockEntry, folder: Path) -> Skill:
        """The skill the entry locks, or an ApplicationError (SKILL_LOCK_MISMATCH) saying how it differs."""

    @abstractmethod
    def verified(self, lock: SkillLock, folder: Path) -> tuple[Skill, ...]:
        """Every skill enabled for some stage, checked, in name order; all the problems at once if any."""

    @abstractmethod
    def problems(self, lock: SkillLock, folder: Path) -> tuple[str, ...]:
        """What no longer matches, for every locked skill, whether or not it is enabled."""
