# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: a voice that reads a piece of text aloud, locally."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.narration import Narration


class NarratorInterface(ABC):
    """One engine and one voice. The domain never imports an audio library: an adapter does."""

    __slots__ = ()

    @abstractmethod
    def narrate(self, text: str) -> Narration:
        """The audio for one segment of plain text. Raise an ApplicationError when the engine cannot."""
