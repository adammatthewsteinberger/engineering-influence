# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: turns a piece of text into narration, and narration into WAV bytes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.narrator_interface import NarratorInterface
    from engineering_influence.models.narration import Narration


class NarrationRendererInterface(ABC):
    """Reads a text in segments with one narrator, and packs the result as 16-bit mono WAV."""

    __slots__ = ()

    @abstractmethod
    def render(self, narrator: NarratorInterface, source: str) -> Narration:
        """The whole text read aloud, segments joined by a short pause. Raise an ApplicationError when it cannot be read."""

    @abstractmethod
    def wav(self, narration: Narration) -> bytes:
        """The narration as a WAV file."""
