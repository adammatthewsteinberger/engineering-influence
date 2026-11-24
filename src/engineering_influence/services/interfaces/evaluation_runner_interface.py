# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EvaluationRunner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.evaluation_case import EvaluationCase
    from engineering_influence.models.evaluation_report import EvaluationReport


class EvaluationRunnerInterface(ABC):
    """Makes and judges every book of the set."""

    __slots__ = ()

    @abstractmethod
    def run(
        self,
        release: str,
        cases: tuple[EvaluationCase, ...],
        budget_micro_usd: int,
        progress: Callable[[str], None],
    ) -> EvaluationReport:
        """Make each case within the budget, judge the books that finished, and report all of them."""
