# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ReleaseGate."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.evaluation_report import EvaluationReport
    from engineering_influence.models.evaluation_verdict import EvaluationVerdict
    from engineering_influence.models.rubric import Rubric


class ReleaseGateInterface(ABC):
    """Decides whether an evaluation meets the bar a release must."""

    __slots__ = ()

    @abstractmethod
    def verdict(
        self, report: EvaluationReport, rubric: Rubric, baseline: Mapping[str, float] | None
    ) -> EvaluationVerdict:
        """Every reason the release does not meet the bar; none means it does."""
