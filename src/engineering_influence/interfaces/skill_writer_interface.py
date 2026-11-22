# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: writing a skill as the bytes of its file."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.skill import Skill


class SkillWriterInterface(ABC):
    """Renders a skill as a skill file, the same bytes every time."""

    __slots__ = ()

    @abstractmethod
    def render(self, skill: Skill) -> bytes:
        """The skill file's bytes, which the skill parser reads back as this skill."""
