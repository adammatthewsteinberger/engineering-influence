# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for LocalBookRun."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_brief import BookBrief
    from engineering_influence.models.book_run import BookRun


class LocalBookRunInterface(ABC):
    """Runs one book from its brief to the end of its plan, in this process, with nobody in the loop."""

    __slots__ = ()

    @abstractmethod
    def start(self, brief: BookBrief, progress: Callable[[str], None]) -> BookRun:
        """Create the run and drive it until it finishes or stops; ``progress`` hears one line per stage."""

    @abstractmethod
    def resume(self, approve_spend: bool, progress: Callable[[str], None]) -> BookRun:
        """Continue the one run this folder holds, from the stage it stopped at."""
