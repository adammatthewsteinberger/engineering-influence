# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: turning a skill file's bytes into a skill."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from typing import Any

    from engineering_influence.models.skill import Skill


class SkillParserInterface(ABC):
    """Reads a skill, strictly, from the bytes of its file."""

    __slots__ = ()

    @abstractmethod
    def parse(self, data: bytes, name: str) -> Skill:
        """The skill, or an ApplicationError (SKILL_INVALID) saying why the file is not one.

        ``name`` is what the file is called without its extension; the file must name itself the same.
        """

    @abstractmethod
    def table(self, raw: Mapping[str, Any], name: str) -> Skill:
        """The skill in an already-read table, checked the same way a skill file is."""
