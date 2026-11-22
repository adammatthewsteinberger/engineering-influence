# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One installed skill, as the lock records it: which text, and which stages may use it."""

import re
from dataclasses import dataclass, replace
from typing import ClassVar

from engineering_influence.models.interfaces.skill_lock_entry_interface import (
    SkillLockEntryInterface,
)
from engineering_influence.models.skill import Skill


@dataclass(frozen=True, slots=True)
class SkillLockEntry(SkillLockEntryInterface):
    """A skill's name, its version, the SHA-256 of its file and the stages it is enabled for.

    The hash is of the file's bytes, so a skill that changes by a single character is a different
    skill and is refused until a person locks it again. The stages are the whole permission: a
    skill that is installed and enabled for no stage is never shown to a model, and a stage the
    entry does not list never sees it. There is no wildcard.
    """

    SHA256: ClassVar[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")

    name: str
    version: int
    sha256: str
    stages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not Skill.NAME.fullmatch(self.name):
            raise ValueError("a locked skill's name is lowercase letters, digits and underscores")
        if type(self.version) is not int or self.version < 1:
            raise ValueError(f"skill {self.name!r} has a version that is not a whole number from 1")
        if not isinstance(self.sha256, str) or not self.SHA256.fullmatch(self.sha256):
            raise ValueError(f"skill {self.name!r} has a hash that is not 64 lowercase hex digits")
        if not isinstance(self.stages, tuple):
            raise TypeError("a skill's stages are a tuple of stage names")
        if any(
            not isinstance(stage, str) or not Skill.NAME.fullmatch(stage) for stage in self.stages
        ):
            raise ValueError(
                f"skill {self.name!r} is enabled for something that is not a stage name"
            )
        if list(self.stages) != sorted(set(self.stages)):
            raise ValueError(f"skill {self.name!r} lists its stages once each, in order")

    def enabled_for(self, stage: str) -> bool:
        """Whether a person enabled this skill for the stage."""
        return stage in self.stages

    def with_stage(self, stage: str) -> "SkillLockEntry":
        """This entry, also enabled for the stage."""
        return replace(self, stages=tuple(sorted({*self.stages, stage})))

    def without_stage(self, stage: str) -> "SkillLockEntry":
        """This entry, no longer enabled for the stage."""
        return replace(self, stages=tuple(name for name in self.stages if name != stage))

    def identity(self) -> str:
        """What a journal key records of this skill: ``plain_style@2:<hash>``."""
        return f"{self.name}@{self.version}:{self.sha256}"
