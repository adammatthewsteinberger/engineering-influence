# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Makes and judges every book of the evaluation set."""

from collections.abc import Callable

from engineering_influence.interfaces.book_maker_interface import BookMakerInterface
from engineering_influence.models.evaluation_case import EvaluationCase
from engineering_influence.models.evaluation_report import EvaluationReport
from engineering_influence.services.interfaces.book_judge_interface import BookJudgeInterface
from engineering_influence.services.interfaces.evaluation_runner_interface import (
    EvaluationRunnerInterface,
)


class EvaluationRunner(EvaluationRunnerInterface):
    """One book at a time, in the set's order: made by the stack's own pipeline, then judged.

    A book that does not finish is reported and not judged. A judge that fails stops the evaluation, because scores
    from a judge that sometimes could not answer would not be comparable with the baseline's.
    """

    def __init__(self, maker: BookMakerInterface, judge: BookJudgeInterface) -> None:
        self._maker = maker
        self._judge = judge

    def run(
        self,
        release: str,
        cases: tuple[EvaluationCase, ...],
        budget_micro_usd: int,
        progress: Callable[[str], None],
    ) -> EvaluationReport:
        """Make each case within the budget, judge the books that finished, and report all of them."""
        results = []
        for case in cases:
            progress(f"{case.name}: making")
            book = self._maker.make(case, budget_micro_usd)
            if book.finished:
                progress(f"{case.name}: judging")
                score = self._judge.judge(book)
                progress(f"{case.name}: " + ", ".join(f"{n} {s}" for n, s, _ in score.scores))
            else:
                score = None
                progress(f"{case.name}: not finished ({book.run_status})")
            results.append((book, score))
        return EvaluationReport(release, tuple(results))
