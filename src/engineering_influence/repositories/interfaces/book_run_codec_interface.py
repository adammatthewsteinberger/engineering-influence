# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookRunCodec."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class BookRunCodecInterface(ABC):
    """Turns a book run into JSON text and back."""

    __slots__ = ()

    @abstractmethod
    def encode(self, run: BookRun) -> str:
        """The run as JSON with sorted keys, so equal runs give equal text."""

    @abstractmethod
    def decode(self, text: str) -> BookRun:
        """The run a previous ``encode`` produced."""
