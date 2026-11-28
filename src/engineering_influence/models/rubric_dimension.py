# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One thing a book is scored on."""

import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.rubric_dimension_interface import (
    RubricDimensionInterface,
)


@dataclass(frozen=True, slots=True)
class RubricDimension(RubricDimensionInterface):
    """A name, the question the judge asks, what 1, 3 and 5 look like, and which kinds of book it applies to.

    The anchors are what keeps a score meaning the same thing from one judge call to the next: a judge told only
    "rate the prose from one to five" drifts. ``kinds`` is a subset of ``nonfiction`` and ``novel``.
    """

    NAME: ClassVar[re.Pattern[str]] = re.compile(r"[a-z][a-z0-9_]*")
    KINDS: ClassVar[frozenset[str]] = frozenset({"nonfiction", "novel"})
    ANCHORS: ClassVar[tuple[int, ...]] = (1, 3, 5)

    name: str
    question: str
    anchors: tuple[tuple[int, str], ...]
    kinds: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate the dimension's name, question and anchors when it is built."""
        if not self.NAME.fullmatch(self.name):
            raise ValueError("a dimension's name is lowercase letters, digits and underscores")
        if not self.question.strip():
            raise ValueError(f"dimension {self.name} needs a question")
        if tuple(score for score, _ in self.anchors) != self.ANCHORS or any(
            not text.strip() for _, text in self.anchors
        ):
            raise ValueError(
                f"dimension {self.name} says what a 1, a 3 and a 5 look like, in that order"
            )
        if (
            not self.kinds
            or not set(self.kinds) <= self.KINDS
            or len(set(self.kinds)) != len(self.kinds)
        ):
            raise ValueError(f"dimension {self.name} applies to nonfiction, novel or both")
