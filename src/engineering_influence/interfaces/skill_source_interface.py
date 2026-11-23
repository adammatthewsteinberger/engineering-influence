# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: where a SKILL.md is read from."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class SkillSourceInterface(ABC):
    """Reads the text of a SKILL.md, from the file or from the folder that holds it."""

    __slots__ = ()

    @abstractmethod
    def read(self, path: Path) -> str:
        """The text, or an ApplicationError (SKILL_SOURCE_INVALID) saying why it cannot be read."""
