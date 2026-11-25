# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EvaluationReporter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.evaluation_report import EvaluationReport
    from engineering_influence.models.evaluation_verdict import EvaluationVerdict
    from engineering_influence.models.rubric import Rubric


class EvaluationReporterInterface(ABC):
    """Writes the evaluation as the JSON document a release is compared against."""

    __slots__ = ()

    @abstractmethod
    def render(self, report: EvaluationReport, verdict: EvaluationVerdict, rubric: Rubric) -> bytes:
        """The evaluation report, as bytes."""
