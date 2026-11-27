# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for VideoShot."""

from __future__ import annotations

from abc import ABC, abstractmethod


class VideoShotInterface(ABC):
    """One shot of a screenplay's video: the model that makes it and how long it runs."""

    __slots__ = ()

    @abstractmethod
    def model(self) -> str:
        """The hosted model's identifier that makes the shot."""

    @abstractmethod
    def seconds(self) -> int:
        """How many seconds of video the shot asks for."""
