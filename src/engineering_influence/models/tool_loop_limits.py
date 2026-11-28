# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How far one tool loop may go."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.tool_loop_limits_interface import (
    ToolLoopLimitsInterface,
)


@dataclass(frozen=True, slots=True)
class ToolLoopLimits(ToolLoopLimitsInterface):
    """Caps on model turns, tool calls, the size of a result and the time of a call.

    A model that keeps asking for tools is bounded by ``max_turns``. Every call to a tool beyond
    ``max_tool_calls`` is answered with a note instead of being run. A result longer than
    ``result_characters`` is cut, with a note of how much, and a tool that has not answered within
    ``call_seconds`` counts as a transient failure.
    """

    max_turns: int = 8
    max_tool_calls: int = 16
    result_characters: int = 20_000
    call_seconds: float = 60.0

    def __post_init__(self) -> None:
        """Validate the caps on turns, calls, result size and call time when they are built."""
        for name in ("max_turns", "max_tool_calls", "result_characters"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} is a whole number from 1")
        if isinstance(self.call_seconds, bool) or not self.call_seconds > 0:
            raise ValueError("call_seconds is more than zero")

    def room_for(self, made: int, asking: int) -> bool:
        """True when ``asking`` more calls still fit under the cap after ``made`` calls."""
        return made + asking <= self.max_tool_calls
