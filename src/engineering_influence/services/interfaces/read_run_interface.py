# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ReadRun."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class ReadRunInterface(ABC):
    """Look at a run and what it has produced, without changing anything."""

    __slots__ = ()

    @abstractmethod
    def summary(self, run_id: str) -> tuple[BookRun, list[str]]:
        """The run and the names of its stored artifacts; ``RUN_NOT_FOUND`` if there is no run."""

    @abstractmethod
    def artifact(self, run_id: str, name: str) -> bytes:
        """One stored artifact; ``ARTIFACT_NOT_FOUND`` if there is none, or the name is invalid."""
