# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a model sent back."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.model_response_interface import (
    ModelResponseInterface,
)
from engineering_influence.models.model_usage import ModelUsage
from engineering_influence.models.tool_call import ToolCall


@dataclass(frozen=True, slots=True)
class ModelResponse(ModelResponseInterface):
    """The text, the tokens it cost, the exact model snapshot and why generation stopped.

    ``stop_reason`` is one of ``end_turn``, ``max_tokens``, ``refusal`` or ``tool_use``; an
    adapter maps its provider's wording onto these so callers never branch on a vendor string.
    ``tool_use`` goes with the tool calls the model asked for, and only with them.
    """

    text: str
    usage: ModelUsage
    model_snapshot: str
    stop_reason: str
    calls: tuple[ToolCall, ...] = ()

    def __post_init__(self) -> None:
        if self.stop_reason not in ("end_turn", "max_tokens", "refusal", "tool_use"):
            raise ValueError(f"unknown stop reason {self.stop_reason!r}")
        if (self.stop_reason == "tool_use") != bool(self.calls):
            raise ValueError("tool_use goes with tool calls, and tool calls with tool_use")
        if len({call.id for call in self.calls}) != len(self.calls):
            raise ValueError("the calls in one response have different ids")
        if not self.model_snapshot.strip():
            raise ValueError("a response names the model snapshot that produced it")

    def was_truncated(self) -> bool:
        """True when the model hit its output cap before it finished."""
        return self.stop_reason == "max_tokens"

    def was_refused(self) -> bool:
        """True when the model declined to answer."""
        return self.stop_reason == "refusal"

    def wants_tools(self) -> bool:
        """True when the model asked for tools to be run before it goes on."""
        return bool(self.calls)
