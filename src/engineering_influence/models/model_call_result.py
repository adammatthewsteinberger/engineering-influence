# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What one guarded model call gave back."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.model_call_result_interface import (
    ModelCallResultInterface,
)
from engineering_influence.models.tool_call import ToolCall


@dataclass(frozen=True, slots=True)
class ModelCallResult(ModelCallResultInterface):
    """The text, why generation stopped, what this call cost now, and whether it was a replay.

    A replayed call cost nothing this time; its original cost is already in the journal.
    ``stop_reason`` is ``end_turn``, ``max_tokens``, ``refusal`` or ``tool_use``, and only
    ``end_turn`` and ``tool_use`` are ever replayed, so a caller can rely on a replay being a
    complete answer. ``tool_use`` goes with the tool calls the model asked for, and only with them.
    """

    text: str
    stop_reason: str
    cost_micro_usd: int
    replayed: bool
    tool_calls: tuple[ToolCall, ...] = ()

    def __post_init__(self) -> None:
        """Validate the call's text, stop reason and cost when it is built."""
        if self.stop_reason not in ("end_turn", "max_tokens", "refusal", "tool_use"):
            raise ValueError(f"unknown stop reason {self.stop_reason!r}")
        if (self.stop_reason == "tool_use") != bool(self.tool_calls):
            raise ValueError("tool_use goes with tool calls, and tool calls with tool_use")
        if self.cost_micro_usd < 0:
            raise ValueError("a call cannot cost less than nothing")
        if self.replayed and (
            self.cost_micro_usd != 0 or self.stop_reason not in ("end_turn", "tool_use")
        ):
            raise ValueError("a replay is free and always a complete answer")
