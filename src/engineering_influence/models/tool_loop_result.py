# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a tool loop gave back."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.tool_loop_result_interface import (
    ToolLoopResultInterface,
)
from engineering_influence.models.model_turn import ModelTurn
from engineering_influence.models.quality_issue import QualityIssue


@dataclass(frozen=True, slots=True)
class ToolLoopResult(ToolLoopResultInterface):
    """The final text, whether the loop finished, and everything that happened on the way.

    A finished loop carries no issues. An unfinished one always says why: the model's answer was
    cut off or declined, or it was still asking for tools when the turns ran out. ``transcript`` is
    each round of the conversation (what the model said and called, and what came back), so a
    caller can see which tools were used and with what.
    """

    text: str
    complete: bool
    issues: tuple[QualityIssue, ...]
    cost_micro_usd: int
    model_calls: int
    tool_calls: int
    turns: int
    transcript: tuple[ModelTurn, ...]

    def __post_init__(self) -> None:
        """Validate the loop's result when it is built."""
        if self.complete and self.issues:
            raise ValueError("a finished loop has no issues")
        if not self.complete and not self.issues:
            raise ValueError("an unfinished loop must say what went wrong")
        if min(self.cost_micro_usd, self.model_calls, self.tool_calls, self.turns) < 0:
            raise ValueError("cost and counts cannot be negative")

    def used_tools(self) -> bool:
        """True when at least one tool was called."""
        return bool(self.transcript)
