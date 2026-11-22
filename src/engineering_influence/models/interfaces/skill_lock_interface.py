# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SkillLock."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.skill_lock import SkillLock
    from engineering_influence.models.skill_lock_entry import SkillLockEntry


class SkillLockInterface(ABC):
    """The skills a person has installed, as written in the skill lock file."""

    __slots__ = ()

    @abstractmethod
    def entry(self, name: str) -> SkillLockEntry | None:
        """The locked skill with this name, or None."""

    @abstractmethod
    def with_entry(self, entry: SkillLockEntry, replace: bool) -> SkillLock:
        """This lock with the entry added; an existing one of that name is replaced only if asked."""

    @abstractmethod
    def without(self, name: str) -> SkillLock:
        """This lock with the skill taken out."""

    @abstractmethod
    def names(self) -> tuple[str, ...]:
        """The locked skills' names, sorted."""

    @abstractmethod
    def enabled(self, stage: str) -> tuple[SkillLockEntry, ...]:
        """The entries enabled for this stage, in name order."""
