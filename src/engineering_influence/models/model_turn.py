# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One round of a conversation with tools: what the model said, what it called, what came back."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.model_turn_interface import ModelTurnInterface
from engineering_influence.models.tool_call import ToolCall
from engineering_influence.models.tool_result import ToolResult


@dataclass(frozen=True, slots=True)
class ModelTurn(ModelTurnInterface):
    """An assistant turn that called tools, with the result of every call.

    A turn is finished: each call has exactly one result and each result answers a call of this
    turn. A conversation that is still waiting for a result is not yet a turn.
    """

    text: str
    calls: tuple[ToolCall, ...]
    results: tuple[ToolResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.calls, tuple) or not self.calls:
            raise ValueError("a turn called at least one tool, in a tuple")
        if not isinstance(self.results, tuple):
            raise TypeError("a turn's results are a tuple")
        called = [call.id for call in self.calls]
        answered = [result.call_id for result in self.results]
        if len(set(called)) != len(called):
            raise ValueError("the calls of one turn have different ids")
        if sorted(called) != sorted(answered):
            raise ValueError("every call of a turn has exactly one result, and no other")

    def result_for(self, call_id: str) -> ToolResult:
        """The result that answers the call with this id."""
        for result in self.results:
            if result.call_id == call_id:
                return result
        raise ValueError(f"this turn has no call {call_id!r}")
