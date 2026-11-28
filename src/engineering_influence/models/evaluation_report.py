# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every book of an evaluation, made and judged."""

from dataclasses import dataclass

from engineering_influence.models.book_score import BookScore
from engineering_influence.models.interfaces.evaluation_report_interface import (
    EvaluationReportInterface,
)
from engineering_influence.models.made_book import MadeBook


@dataclass(frozen=True, slots=True)
class EvaluationReport(EvaluationReportInterface):
    """The release's label, and for each case the book made and the score it was given (none if it was not finished)."""

    release: str
    results: tuple[tuple[MadeBook, BookScore | None], ...]

    def __post_init__(self) -> None:
        """Validate the report's label and cases when it is built."""
        if not self.release.strip():
            raise ValueError("an evaluation names the release it measured")
        cases = [book.case for book, _ in self.results]
        if not cases or len(set(cases)) != len(cases):
            raise ValueError("an evaluation has books, each case once")
        for book, score in self.results:
            if (score is None) == book.finished:
                raise ValueError(
                    f"{book.case}: a finished book is scored and an unfinished one is not"
                )
            if score is not None and score.case != book.case:
                raise ValueError(f"{book.case}: the score is for another case")

    def means(self) -> dict[str, float]:
        """The mean score of each dimension over the books that were scored, to two places."""
        totals: dict[str, list[int]] = {}
        for _, score in self.results:
            if score is not None:
                for name, value in score.by_name().items():
                    totals.setdefault(name, []).append(value)
        return {
            name: round(sum(values) / len(values), 2) for name, values in sorted(totals.items())
        }

    def spent(self) -> int:
        """What making the books cost, in micro-dollars."""
        return sum(book.spent_micro_usd for book, _ in self.results)

    def estimated(self) -> int | None:
        """What the books were expected to cost, or None when any had no estimate."""
        figures = [book.estimated_micro_usd for book, _ in self.results]
        return (
            None
            if any(figure is None for figure in figures)
            else sum(f for f in figures if f is not None)
        )

    def judged(self) -> int:
        """What judging cost, in micro-dollars."""
        return sum(score.judge_micro_usd for _, score in self.results if score is not None)
