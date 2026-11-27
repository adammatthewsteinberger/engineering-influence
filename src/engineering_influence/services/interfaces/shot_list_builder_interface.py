# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ShotListBuilder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.video_shot import VideoShot


class ShotListBuilderInterface(ABC):
    """Turns a screenplay into the shots its video is made of."""

    __slots__ = ()

    @abstractmethod
    def build(self, script: str) -> tuple[VideoShot, ...]:
        """Every shot of the script, in order, each with its model, length and prompt."""
