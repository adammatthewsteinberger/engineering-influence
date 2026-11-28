# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: revises one drafted scene of a screenplay, given the card it must still serve."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun
    from engineering_influence.models.scene_card import SceneCard


class SceneReviserInterface(ABC):
    """One scene per call. An adapter calls a model; the domain never does."""

    __slots__ = ()

    @abstractmethod
    def revise(self, run: BookRun, card: SceneCard, scene: str) -> str:
        """The revised scene as Fountain. Raise an ApplicationError when the answer cannot be used at all."""
