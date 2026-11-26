# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SceneCardList."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.scene_card import SceneCard


class SceneCardListInterface(ABC):
    """Reads a screenplay's scene cards."""

    __slots__ = ()

    @abstractmethod
    def parse(self, text: str) -> tuple[SceneCard, ...]:
        """Every card in the text, or an ApplicationError when the cards cannot be read."""
