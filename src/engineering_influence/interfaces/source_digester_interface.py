# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SourceDigester."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class SourceDigesterInterface(ABC):
    """Condenses one source file for a screenplay. An adapter calls a model; the domain never does."""

    __slots__ = ()

    @abstractmethod
    def digest(self, run: BookRun, source: str) -> str:
        """The condensed source as plain prose. Raise an ApplicationError when the answer cannot be used at all."""
