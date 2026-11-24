# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CostEstimator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_brief import BookBrief
    from engineering_influence.models.cost_estimate import CostEstimate


class CostEstimatorInterface(ABC):
    """Says what a book is expected to cost, from its brief, with a particular model's prices."""

    __slots__ = ()

    @abstractmethod
    def estimate(self, brief: BookBrief) -> CostEstimate:
        """The expected cost of every stage of the plan for the brief's kind of book."""
