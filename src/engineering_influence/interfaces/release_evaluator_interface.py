# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: evaluating a release against the rubric."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.evaluation_verdict import EvaluationVerdict


class ReleaseEvaluatorInterface(ABC):
    """Makes the evaluation set into books, judges them, and says whether the release meets the bar."""

    __slots__ = ()

    @abstractmethod
    def evaluate(
        self,
        release: str,
        budget_micro_usd: int,
        judge_budget_micro_usd: int,
        progress: Callable[[str], None],
    ) -> tuple[bytes, EvaluationVerdict]:
        """The evaluation report as bytes, and the verdict on it."""
