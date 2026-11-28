# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for NarrationGate."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.narration import Narration


class NarrationGateInterface(ABC):
    """Decides whether a chapter's audio is fit to keep, and levels the audio that is."""

    __slots__ = ()

    @abstractmethod
    def problems(self, narration: Narration, words: int) -> tuple[str, ...]:
        """Why the audio must not be kept, or nothing when it may be."""

    @abstractmethod
    def normalise(self, narration: Narration) -> Narration:
        """The audio levelled to the store's loudness, never clipped. Call it only on audio that passed."""
