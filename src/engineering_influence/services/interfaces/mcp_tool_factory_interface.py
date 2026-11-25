# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpToolFactory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.tool_interface import ToolInterface
    from engineering_influence.services.interfaces.mcp_connection_interface import (
        McpConnectionInterface,
    )


class McpToolFactoryInterface(ABC):
    """Makes a tool for each of a server's tools that can be offered to a model."""

    __slots__ = ()

    @abstractmethod
    def create(self, connection: McpConnectionInterface) -> tuple[ToolInterface, ...]:
        """One tool per offerable tool the server advertised, in name order."""
