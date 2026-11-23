# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SkillConverter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.skill import Skill
    from engineering_influence.models.skill_document import SkillDocument


class SkillConverterInterface(ABC):
    """Turns chosen sections of a SKILL.md into a skill for some stages."""

    __slots__ = ()

    @abstractmethod
    def convert(
        self,
        document: SkillDocument,
        name: str | None,
        version: int,
        stages: tuple[str, ...],
        titles: tuple[str, ...],
    ) -> Skill:
        """The skill, or an ApplicationError (SKILL_IMPORT_INVALID, SKILL_IMPORT_TOO_LARGE) saying what to change."""

    @abstractmethod
    def sections(self, document: SkillDocument, titles: tuple[str, ...]) -> tuple[str, ...]:
        """The titles of the sections ``convert`` would use for these choices, in the order they appear."""
