# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One tool an MCP server advertises."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from engineering_influence.models.interfaces.mcp_tool_descriptor_interface import (
    McpToolDescriptorInterface,
)
from engineering_influence.models.tool_definition import ToolDefinition


@dataclass(frozen=True, slots=True)
class McpToolDescriptor(McpToolDescriptorInterface):
    """The name, description and input schema a server gave for one tool.

    All three are text the server wrote, and the description is the place a hostile server hides
    instructions for the model. That is why a server's whole set of descriptors is hashed into the
    lock: a changed description is a changed server. A tool is offered to a model under the name
    ``<server>__<tool>``, which has to fit what the providers accept; one that does not is not offered.
    """

    SEPARATOR = "__"

    name: str
    description: str
    input_schema: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Validate the tool's name, description and schema when it is built."""
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("an MCP tool has a name")
        if not isinstance(self.description, str):
            raise TypeError("an MCP tool's description is text")
        if not isinstance(self.input_schema, Mapping):
            raise TypeError("an MCP tool's input schema is a JSON object")
        try:
            json.dumps(self.input_schema)
        except (TypeError, ValueError) as error:
            raise ValueError("an MCP tool's input schema must be plain JSON") from error

    def model_name(self, server: str) -> str:
        """The name the model sees: the server's lock name, two underscores, the tool's name."""
        return f"{server}{self.SEPARATOR}{self.name}"

    def offerable(self, server: str) -> bool:
        """True when the tool can be offered: its model name is valid and it takes an object."""
        return (
            ToolDefinition.NAME.fullmatch(self.model_name(server)) is not None
            and self.input_schema.get("type") == "object"
        )

    def definition(self, server: str) -> ToolDefinition:
        """What the model is told about this tool."""
        described = (
            self.description.strip() or f"The {self.name} tool (its server gave no description)."
        )
        return ToolDefinition(self.model_name(server), described, self.input_schema)

    def canonical(self) -> dict[str, Any]:
        """The descriptor as plain JSON, the form that is hashed."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": json.loads(json.dumps(self.input_schema)),
        }
