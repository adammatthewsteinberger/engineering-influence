# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FountainParser."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.fountain_block import FountainBlock
    from engineering_influence.models.fountain_scene import FountainScene


class FountainParserInterface(ABC):
    """Reads a Fountain screenplay into its title page, its elements and its scenes."""

    __slots__ = ()

    @abstractmethod
    def title_page(self, text: str) -> tuple[tuple[str, str], ...]:
        """The title page's (key, value) pairs in order, or none when the script has no title page."""

    @abstractmethod
    def blocks(self, text: str) -> tuple[FountainBlock, ...]:
        """Every element after the title page, with boneyard and notes taken out."""

    @abstractmethod
    def scenes(self, text: str) -> tuple[FountainScene, ...]:
        """Every scene, numbered from 1, in the order it appears."""
