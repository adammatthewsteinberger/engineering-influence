# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpClient."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engineering_influence.models.mcp_call_result import McpCallResult
    from engineering_influence.models.mcp_server_info import McpServerInfo
    from engineering_influence.models.mcp_tool_set import McpToolSet


class McpClientInterface(ABC):
    """Speaks the Model Context Protocol to one server, as a client that offers it nothing."""

    __slots__ = ()

    @abstractmethod
    def initialize(self) -> McpServerInfo:
        """Start the session and return who the server says it is."""

    @abstractmethod
    def list_tools(self) -> McpToolSet:
        """Every tool the server advertises."""

    @abstractmethod
    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> McpCallResult:
        """Call one tool and return its text answer."""

    @abstractmethod
    def close(self) -> None:
        """End the session."""
