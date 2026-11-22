# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: the installed text a stage's prompt carries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.guidance import Guidance


class StageGuidanceInterface(ABC):
    """What the skills a person enabled for a stage add to that stage's prompt."""

    __slots__ = ()

    @abstractmethod
    def for_stage(self, stage: str) -> Guidance:
        """The text and identity to add for the stage; empty guidance when no skill is enabled for it."""
