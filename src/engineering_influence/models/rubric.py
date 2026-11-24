# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The rubric a release is held to."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.rubric_interface import RubricInterface
from engineering_influence.models.rubric_dimension import RubricDimension


@dataclass(frozen=True, slots=True)
class Rubric(RubricInterface):
    """Scores run from ``LOW`` to ``HIGH``; a release passes when the mean of every dimension reaches ``pass_mean``
    and no dimension's mean has fallen by more than ``max_drop`` since the baseline (the previous release).

    The two thresholds are the ones ADR 0003 sets (3.5 and 0.2); they live in the rubric file so that a rubric and its
    bar are one reviewed document.
    """

    LOW: ClassVar[int] = 1
    HIGH: ClassVar[int] = 5

    version: int
    pass_mean: float
    max_drop: float
    dimensions: tuple[RubricDimension, ...]

    def __post_init__(self) -> None:
        if type(self.version) is not int or self.version < 1:
            raise ValueError("a rubric has a version, 1 or more")
        if not self.LOW <= self.pass_mean <= self.HIGH:
            raise ValueError(f"the pass mark is between {self.LOW} and {self.HIGH}")
        if not 0 <= self.max_drop < self.HIGH - self.LOW:
            raise ValueError("the allowed drop is not negative and is less than the whole scale")
        names = [dimension.name for dimension in self.dimensions]
        if not names or len(set(names)) != len(names):
            raise ValueError("a rubric has dimensions, each named once")
        for kind in RubricDimension.KINDS:
            if not self.for_kind(kind):
                raise ValueError(f"a rubric needs at least one dimension for {kind}")

    def for_kind(self, kind: str) -> tuple[RubricDimension, ...]:
        """The dimensions a book of this kind is scored on."""
        return tuple(dimension for dimension in self.dimensions if kind in dimension.kinds)

    def render(self, kind: str) -> str:
        """The rubric as the judge reads it: each dimension, its question and what 1, 3 and 5 mean."""
        blocks = []
        for dimension in self.for_kind(kind):
            anchors = "\n".join(f"  {score}: {text}" for score, text in dimension.anchors)
            blocks.append(f"{dimension.name}: {dimension.question}\n{anchors}")
        return "\n\n".join(blocks)
