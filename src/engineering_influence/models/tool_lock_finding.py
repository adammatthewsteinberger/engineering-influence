# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The result of checking one locked server."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.tool_lock_finding_interface import (
    ToolLockFindingInterface,
)


@dataclass(frozen=True, slots=True)
class ToolLockFinding(ToolLockFindingInterface):
    """A locked server's name and what is wrong with it; no problems means it is as approved.

    Problems can quote what a server said, so they are shown with anything that is not printable
    (control characters, escape sequences) replaced by a space.
    """

    name: str
    problems: tuple[str, ...]

    def passed(self) -> bool:
        """True when nothing differs from what was approved."""
        return not self.problems

    def lines(self) -> tuple[str, ...]:
        """The lines to print: one ``ok`` line, or one ``FAIL`` line per problem."""
        if not self.problems:
            return (f"ok    {self.name}",)
        return tuple(f"FAIL  {self.name}: {self._clean(problem)}" for problem in self.problems)

    @staticmethod
    def _clean(text: str) -> str:
        return "".join(char if char.isprintable() else " " for char in text)
