# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpConnection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engineering_influence.models.mcp_call_result import McpCallResult
    from engineering_influence.models.mcp_tool_set import McpToolSet


class McpConnectionInterface(ABC):
    """A started, verified locked server that tools can be called through."""

    __slots__ = ()

    @abstractmethod
    def server(self) -> str:
        """The server's name in the lock."""

    @abstractmethod
    def tools(self) -> McpToolSet:
        """Every tool the server advertised, which matched the lock when it was started."""

    @abstractmethod
    def call(self, name: str, arguments: Mapping[str, Any]) -> McpCallResult:
        """Call one of the server's tools; one call at a time."""

    @abstractmethod
    def close(self) -> None:
        """Stop the server."""
