# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpToolDescriptor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engineering_influence.models.tool_definition import ToolDefinition


class McpToolDescriptorInterface(ABC):
    """One tool an MCP server advertises."""

    __slots__ = ()

    @abstractmethod
    def model_name(self, server: str) -> str:
        """The name the model sees: the server's lock name, two underscores, the tool's name."""

    @abstractmethod
    def offerable(self, server: str) -> bool:
        """True when the tool can be offered: its model name is valid and it takes an object."""

    @abstractmethod
    def definition(self, server: str) -> ToolDefinition:
        """What the model is told about this tool."""

    @abstractmethod
    def canonical(self) -> dict[str, Any]:
        """The descriptor as plain JSON, the form that is hashed."""
