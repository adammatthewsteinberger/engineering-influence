# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: where a new skill file is written."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class SkillSinkInterface(ABC):
    """Writes a skill file that did not exist, and never replaces one."""

    __slots__ = ()

    @abstractmethod
    def write_new(self, path: Path, data: bytes) -> None:
        """Create the file, or raise an ApplicationError (SKILL_TARGET_EXISTS) when something is already there."""
