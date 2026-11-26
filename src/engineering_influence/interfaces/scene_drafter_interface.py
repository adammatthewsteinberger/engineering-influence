# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: drafts one scene of a screenplay from its card, the anchors and the beat sheet."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun
    from engineering_influence.models.scene_card import SceneCard


class SceneDrafterInterface(ABC):
    """One scene per call. An adapter calls a model; the domain never does."""

    __slots__ = ()

    @abstractmethod
    def draft(
        self, run: BookRun, card: SceneCard, anchors: str, beats: str, try_number: int
    ) -> str:
        """The scene as Fountain: its heading and its elements. Raise an ApplicationError when no scene can be drafted."""
