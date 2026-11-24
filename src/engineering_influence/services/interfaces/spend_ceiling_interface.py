# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SpendCeiling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class SpendCeilingInterface(ABC):
    """Refuses a run, or a raise of its cap, that would break the operator's ceilings."""

    __slots__ = ()

    @abstractmethod
    def admit_new(self, cap: int) -> None:
        """Return when a new run with this cap fits; raise an ApplicationError that says which ceiling it would break."""

    @abstractmethod
    def admit_raise(self, run: BookRun, extra: int) -> None:
        """Return when raising this run's cap by ``extra`` fits; raise an ApplicationError when it does not."""

    @abstractmethod
    def outstanding(self) -> int:
        """The unspent budget of every unfinished run, in micro-dollars."""
