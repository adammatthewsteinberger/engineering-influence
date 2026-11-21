# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One call a model asked for: which tool, and with what arguments."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from engineering_influence.models.interfaces.tool_call_interface import ToolCallInterface
from engineering_influence.models.tool_definition import ToolDefinition


@dataclass(frozen=True, slots=True)
class ToolCall(ToolCallInterface):
    """The provider's id for the call, the tool's name and its arguments as plain JSON.

    Nothing here runs the call. A call is only what the model said; whether the tool exists for
    this stage, and what it returns, is decided elsewhere.
    """

    id: str
    name: str
    arguments: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("a tool call has the id the provider gave it")
        if not ToolDefinition.NAME.fullmatch(self.name):
            raise ValueError("a tool call names a tool with 1 to 64 letters, digits, - or _")
        if not isinstance(self.arguments, Mapping):
            raise TypeError("a tool call's arguments are a JSON object")
        try:
            json.dumps(self.arguments)
        except (TypeError, ValueError) as error:
            raise ValueError("a tool call's arguments must be plain JSON") from error

    def arguments_json(self) -> str:
        """The arguments as one canonical line of JSON: the same call always gives the same text."""
        return json.dumps(self.arguments, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
