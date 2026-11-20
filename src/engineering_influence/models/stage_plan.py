# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ordered stages a run walks through for one kind of book."""

from dataclasses import dataclass

from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.interfaces.stage_plan_interface import StagePlanInterface


@dataclass(frozen=True, slots=True)
class StagePlan(StagePlanInterface):
    """Stage names in the order they run; a stage appears once."""

    kind: BookKind
    stages: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.stages or any(not stage.strip() for stage in self.stages):
            raise ValueError("a plan needs at least one named stage")
        if len(set(self.stages)) != len(self.stages):
            raise ValueError("plan stages must be distinct")

    def first(self) -> str:
        """The stage a new run starts on."""
        return self.stages[0]

    def after(self, stage: str) -> str | None:
        """The stage that follows ``stage``, or None after the last one."""
        if stage not in self.stages:
            raise ValueError(f"{stage!r} is not a stage of this plan")
        position = self.stages.index(stage) + 1
        return self.stages[position] if position < len(self.stages) else None
