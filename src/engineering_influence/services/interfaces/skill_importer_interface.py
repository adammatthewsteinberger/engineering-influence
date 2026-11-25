# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SkillImporter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.skill_import_result import SkillImportResult


class SkillImporterInterface(ABC):
    """Reads a SKILL.md and writes a skill file for review; it locks and enables nothing."""

    __slots__ = ()

    @abstractmethod
    def import_skill(
        self,
        source: Path,
        name: str | None,
        version: int,
        stages: tuple[str, ...],
        titles: tuple[str, ...],
        reference: bool,
        target: Path | None,
    ) -> SkillImportResult:
        """Write the skill file and say what it holds, or raise an ApplicationError saying what to change."""
