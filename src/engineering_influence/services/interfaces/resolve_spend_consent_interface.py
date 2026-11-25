# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ResolveSpendConsent."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun


class ResolveSpendConsentInterface(ABC):
    """Answers a run's request for more budget: grant it, or deny it."""

    __slots__ = ()

    @abstractmethod
    def grant(self, run_id: str, micro_usd: int | None = None) -> BookRun:
        """Raise the cap and queue the run's stage."""

    @abstractmethod
    def deny(self, run_id: str) -> BookRun:
        """Refuse the request: the run parks until it is granted more budget."""
