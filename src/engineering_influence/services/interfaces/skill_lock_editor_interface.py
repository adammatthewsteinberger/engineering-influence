# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SkillLockEditor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.skill_lock import SkillLock
    from engineering_influence.models.skill_lock_addition import SkillLockAddition


class SkillLockEditorInterface(ABC):
    """Installs a skill into the lock, enables it for stages, and takes it out again."""

    __slots__ = ()

    @abstractmethod
    def add(self, lock: SkillLock, folder: Path, source: Path, replace: bool) -> SkillLockAddition:
        """Lock the skill in ``source`` and keep a copy in ``folder``; nothing is enabled."""

    @abstractmethod
    def add_bytes(
        self, lock: SkillLock, folder: Path, name: str, data: bytes, replace: bool
    ) -> SkillLockAddition:
        """Lock a skill given as the bytes of its file and keep them in ``folder``; nothing is enabled."""

    @abstractmethod
    def enable(self, lock: SkillLock, folder: Path, name: str, stage: str) -> SkillLock:
        """The lock with the skill enabled for the stage."""

    @abstractmethod
    def disable(self, lock: SkillLock, name: str, stage: str) -> SkillLock:
        """The lock with the skill no longer enabled for the stage."""

    @abstractmethod
    def remove(self, lock: SkillLock, folder: Path, name: str) -> SkillLock:
        """The lock without the skill, and its copy deleted from ``folder``."""
