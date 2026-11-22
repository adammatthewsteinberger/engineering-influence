# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SkillLockEntry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.skill_lock_entry import SkillLockEntry


class SkillLockEntryInterface(ABC):
    """One installed skill, as the lock records it: which text, and which stages may use it."""

    __slots__ = ()

    @abstractmethod
    def enabled_for(self, stage: str) -> bool:
        """Whether a person enabled this skill for the stage."""

    @abstractmethod
    def with_stage(self, stage: str) -> SkillLockEntry:
        """This entry, also enabled for the stage."""

    @abstractmethod
    def without_stage(self, stage: str) -> SkillLockEntry:
        """This entry, no longer enabled for the stage."""

    @abstractmethod
    def identity(self) -> str:
        """What a journal key records of this skill: ``plain_style@2:<hash>``."""
