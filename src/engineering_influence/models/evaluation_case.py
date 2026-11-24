# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One book of the evaluation set."""

import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.interfaces.evaluation_case_interface import (
    EvaluationCaseInterface,
)


@dataclass(frozen=True, slots=True)
class EvaluationCase(EvaluationCaseInterface):
    """A named idea of one kind, the same on every release, so scores can be compared.

    The set is the benchmark: change an idea and the baseline no longer measures the same thing, so a set is edited
    only with a new baseline.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9-]*")

    name: str
    kind: BookKind
    idea: str
    title_hint: str | None = None
    target_words: int | None = None
    trim_size: str | None = None

    def __post_init__(self) -> None:
        if not self.NAME.fullmatch(self.name):
            raise ValueError("a case's name is lowercase letters, digits and hyphens")
        if not self.idea.strip():
            raise ValueError(f"case {self.name} needs an idea")
        if self.target_words is not None and (
            type(self.target_words) is not int or self.target_words < 1
        ):
            raise ValueError(f"case {self.name}: the target is a whole number of words, 1 or more")

    def brief(self, budget_micro_usd: int) -> BookBrief:
        """The brief the run is started from, with the budget this evaluation gives each book."""
        return BookBrief(
            kind=self.kind,
            idea=self.idea,
            budget_micro_usd=budget_micro_usd,
            title_hint=self.title_hint,
            target_words=self.target_words,
            trim_size=self.trim_size,
        )
