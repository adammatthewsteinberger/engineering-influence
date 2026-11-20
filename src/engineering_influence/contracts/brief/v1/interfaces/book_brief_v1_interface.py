# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookBriefV1."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_brief import BookBrief


class BookBriefV1Interface(ABC):
    """Version 1 of the brief: the one document that starts a book run."""

    __slots__ = ()

    @abstractmethod
    def to_model(self) -> BookBrief:
        """The same brief as the pure model a run is built from."""
