# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SkillMarkdownParser."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.skill_document import SkillDocument


class SkillMarkdownParserInterface(ABC):
    """Reads a SKILL.md into a name, a description and sections, strictly."""

    __slots__ = ()

    @abstractmethod
    def parse(self, text: str) -> SkillDocument:
        """The document, or an ApplicationError (SKILL_MARKDOWN_INVALID) saying what is wrong with the file."""
