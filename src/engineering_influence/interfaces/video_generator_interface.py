# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for VideoGenerator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.video_shot import VideoShot


class VideoGeneratorInterface(ABC):
    """Makes one shot of video with a hosted model. The domain never calls a service: an adapter does."""

    __slots__ = ()

    @abstractmethod
    def generate(self, shot: VideoShot) -> bytes:
        """The video file's bytes for the shot. Raise an ApplicationError when the service cannot make it."""
