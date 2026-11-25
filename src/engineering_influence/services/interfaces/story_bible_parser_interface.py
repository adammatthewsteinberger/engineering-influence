# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for StoryBibleParser."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.story_bible import StoryBible


class StoryBibleParserInterface(ABC):
    """Reads the story bible stage's JSON into a story bible, strictly."""

    __slots__ = ()

    @abstractmethod
    def parse(self, text: str) -> StoryBible:
        """The bible, or an ApplicationError (STORY_BIBLE_INVALID) saying what is wrong with the text."""
