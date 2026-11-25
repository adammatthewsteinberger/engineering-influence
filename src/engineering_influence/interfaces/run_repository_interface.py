# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Run repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class RunRepositoryInterface(ABC):
    """Store book runs so a stopped run can be loaded and continued."""

    __slots__ = ()

    @abstractmethod
    def save(self, run: BookRun) -> None:
        """Store the run, replacing any earlier state saved under the same id."""

    @abstractmethod
    def swap(self, expected: BookRun, replacement: BookRun) -> bool:
        """Store ``replacement`` only if the stored run is still exactly ``expected``.

        Returns False, changing nothing, when another worker changed the run first or the run
        was never saved. This is how two deliveries of one stage avoid overwriting each other.
        """

    @abstractmethod
    def get(self, run_id: str) -> BookRun | None:
        """The last saved state of a run, or None if it was never saved."""

    @abstractmethod
    def run_ids(self) -> list[str]:
        """Every saved run id, in sorted order."""
