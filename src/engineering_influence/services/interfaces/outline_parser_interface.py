# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for OutlineParser."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.outline import Outline


class OutlineParserInterface(ABC):
    """Reads the outline stage's markdown into chapters, strictly."""

    __slots__ = ()

    @abstractmethod
    def parse(self, text: str) -> Outline:
        """The outline, or an ApplicationError (OUTLINE_INVALID) saying what is wrong with the text."""
