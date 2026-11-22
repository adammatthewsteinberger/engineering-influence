# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a server said about itself when it was started and asked."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.mcp_server_inspection_interface import (
    McpServerInspectionInterface,
)
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_tool_set import McpToolSet


@dataclass(frozen=True, slots=True)
class McpServerInspection(McpServerInspectionInterface):
    """The server's reported name and version, and every tool it advertised."""

    info: McpServerInfo
    tools: McpToolSet
