# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for NonfictionRevisionPasses."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.revision_pass import RevisionPass


class RevisionPassesInterface(ABC):
    """The editing passes a book goes through after it is drafted, in order."""

    __slots__ = ()

    @abstractmethod
    def passes(self) -> tuple[RevisionPass, ...]:
        """The passes, each reading the files the one before it wrote."""

    @abstractmethod
    def final(self) -> str:
        """The file prefix the last pass writes, which is what the book is assembled from."""
