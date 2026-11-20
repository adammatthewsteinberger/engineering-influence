# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for AdvanceRun."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.advance_outcome import AdvanceOutcome


class AdvanceRunInterface(ABC):
    """Move a book run one stage forward, however many times the message arrives."""

    __slots__ = ()

    @abstractmethod
    async def advance(self, run_id: str, stage: str, attempt: int) -> AdvanceOutcome:
        """Handle one delivery of an advance message for a stage of a run."""
