# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the judge said about one book."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.book_score_interface import BookScoreInterface
from engineering_influence.models.rubric import Rubric


@dataclass(frozen=True, slots=True)
class BookScore(BookScoreInterface):
    """A whole-number score from ``Rubric.LOW`` to ``Rubric.HIGH`` and a reason for each dimension, and what judging cost."""

    case: str
    scores: tuple[tuple[str, int, str], ...]
    judge_micro_usd: int

    def __post_init__(self) -> None:
        """Validate that every dimension has a score within the rubric range and a reason."""
        names = [name for name, _, _ in self.scores]
        if not self.scores or len(set(names)) != len(names):
            raise ValueError("a book is scored on each dimension once")
        for name, score, reason in self.scores:
            if type(score) is not int or not Rubric.LOW <= score <= Rubric.HIGH:
                raise ValueError(
                    f"{name}: a score is a whole number from {Rubric.LOW} to {Rubric.HIGH}"
                )
            if not reason.strip():
                raise ValueError(f"{name}: a score comes with its reason")
        if type(self.judge_micro_usd) is not int or self.judge_micro_usd < 0:
            raise ValueError("what judging cost is a whole number of micro-dollars")

    def by_name(self) -> dict[str, int]:
        """Dimension name to score."""
        return {name: score for name, score, _ in self.scores}
