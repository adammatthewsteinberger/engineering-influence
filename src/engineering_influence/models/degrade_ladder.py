# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An ordered list of ever-cheaper ways to carry on when a stage keeps failing."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.degrade_ladder_interface import (
    DegradeLadderInterface,
)


@dataclass(frozen=True, slots=True)
class DegradeLadder(DegradeLadderInterface):
    """Rungs from best to cheapest; a run steps down one rung at a time, never back up."""

    rungs: tuple[str, ...]
    position: int = 0

    def __post_init__(self) -> None:
        if not self.rungs or any(not rung.strip() for rung in self.rungs):
            raise ValueError("a ladder needs at least one named rung")
        if len(set(self.rungs)) != len(self.rungs):
            raise ValueError("ladder rungs must be distinct")
        if not 0 <= self.position < len(self.rungs):
            raise ValueError("ladder position is off the ladder")

    def current(self) -> str:
        """The rung the run is on now."""
        return self.rungs[self.position]

    def exhausted(self) -> bool:
        """True on the last rung, where there is nothing cheaper to try."""
        return self.position == len(self.rungs) - 1

    def step_down(self) -> "DegradeLadder":
        """The ladder one rung lower; stepping off the bottom is an error."""
        if self.exhausted():
            raise ValueError("the ladder has no lower rung")
        return DegradeLadder(rungs=self.rungs, position=self.position + 1)
