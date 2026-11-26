# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Narration."""

from __future__ import annotations

from abc import ABC, abstractmethod


class NarrationInterface(ABC):
    """Mono audio: samples in the range -1 to 1 at a sample rate."""

    __slots__ = ()

    @abstractmethod
    def seconds(self) -> float:
        """How long the audio plays."""
