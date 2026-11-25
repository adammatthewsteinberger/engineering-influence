# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: making one book of the evaluation set."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.evaluation_case import EvaluationCase
    from engineering_influence.models.made_book import MadeBook


class BookMakerInterface(ABC):
    """Makes a case into a book with the stack's own pipeline, and says how it went."""

    __slots__ = ()

    @abstractmethod
    def make(self, case: EvaluationCase, budget_micro_usd: int) -> MadeBook:
        """Run the case to the end of its plan within the budget; a run that does not finish is described, not raised."""
