# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RunProgress."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class RunProgressInterface(ABC):
    """Reads where a run is now, for a client that follows it."""

    __slots__ = ()

    @abstractmethod
    def current(self, run_id: str) -> BookRun | None:
        """The run's last saved state, or None if no run has that id."""
