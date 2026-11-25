# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The bar a release must meet."""

from collections.abc import Mapping
from typing import ClassVar

from engineering_influence.models.evaluation_report import EvaluationReport
from engineering_influence.models.evaluation_verdict import EvaluationVerdict
from engineering_influence.models.rubric import Rubric
from engineering_influence.services.interfaces.release_gate_interface import ReleaseGateInterface


class ReleaseGate(ReleaseGateInterface):
    """ADR 0003, criteria A5 and A6, as a function of one evaluation and the last one.

    **Every book finishes.** A book that did not is a failure of the release, not a missing data point: leaving it out
    would let a pipeline that breaks on hard ideas pass by scoring only the easy ones.

    **Every dimension's mean reaches the rubric's pass mark** (3.5 of 5), and **none has fallen by more than the allowed
    drop** (0.2) since the baseline, which is the previous release's means. A dimension the baseline had and this
    evaluation did not measure is a failure too.

    **The cost estimate was within ``ESTIMATE_TOLERANCE_PERCENT`` of what was really spent**, over the whole set: the
    estimate the brief gave beside what the books cost. No estimate while money was spent is a failure, because the
    check cannot be made.
    """

    ESTIMATE_TOLERANCE_PERCENT: ClassVar[int] = 30

    def verdict(
        self, report: EvaluationReport, rubric: Rubric, baseline: Mapping[str, float] | None
    ) -> EvaluationVerdict:
        """Every reason the release does not meet the bar; none means it does."""
        failures = [
            f"{book.case}: the book was not finished ({book.run_status})"
            for book, _ in report.results
            if not book.finished
        ]
        means = report.means()
        for name, mean in means.items():
            if mean < rubric.pass_mean:
                failures.append(
                    f"{name}: the mean {mean} is below the pass mark {rubric.pass_mean}"
                )
        for name, earlier in sorted((baseline or {}).items()):
            if name not in means:
                failures.append(f"{name}: the baseline measured it and this evaluation did not")
            elif round(earlier - means[name], 2) > rubric.max_drop:
                failures.append(
                    f"{name}: the mean fell from {earlier} to {means[name]}, more than the allowed {rubric.max_drop}"
                )
        failures.extend(self._estimate(report))
        return EvaluationVerdict(tuple(failures))

    def _estimate(self, report: EvaluationReport) -> list[str]:
        spent, expected = report.spent(), report.estimated()
        if spent == 0:
            return []
        if expected is None:
            return [
                "no cost estimate was recorded for some book, so its accuracy cannot be checked"
            ]
        off = abs(expected - spent) * 100 / spent
        if off > self.ESTIMATE_TOLERANCE_PERCENT:
            return [
                (
                    f"the cost estimate was {expected} micro-USD against {spent} spent: {off:.0f}% off, "
                    f"more than the allowed {self.ESTIMATE_TOLERANCE_PERCENT}%"
                )
            ]
        return []
