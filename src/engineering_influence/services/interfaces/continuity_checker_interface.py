# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ContinuityChecker."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.continuity_finding import ContinuityFinding
    from engineering_influence.models.story_bible import StoryBible


class ContinuityCheckerInterface(ABC):
    """Reads a novel's chapters against its story bible, with no model, and reports where they disagree."""

    __slots__ = ()

    @abstractmethod
    def check(self, bible: StoryBible, chapters: tuple[str, ...]) -> tuple[ContinuityFinding, ...]:
        """The findings, in chapter order, for chapters numbered from 1 in the order given."""
