# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for VideoCost."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.video_shot import VideoShot


class VideoCostInterface(ABC):
    """What a set of shots costs to generate, before any paid call is made."""

    __slots__ = ()

    @abstractmethod
    def cost_micro_usd(self, shots: tuple[VideoShot, ...]) -> int:
        """The cost in micro-dollars of generating the shots, including the takes that are not kept."""
