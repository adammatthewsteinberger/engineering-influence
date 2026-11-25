# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpApplication."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class McpApplicationInterface(ABC):
    """Expose pipeline tools through the official MCP SDK's `MCPServer` (mcp 2.x)."""

    __slots__ = ()

    @abstractmethod
    def build(self) -> Any:
        """Build a server with a typed `start_pipeline` tool."""

    @abstractmethod
    async def run_stdio(self) -> None:
        """Run the server over MCP stdio transport."""
