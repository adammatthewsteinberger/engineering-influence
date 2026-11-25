# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Turns what a verified server advertised into tools the runner can call."""

from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.services.interfaces.mcp_connection_interface import (
    McpConnectionInterface,
)
from engineering_influence.services.interfaces.mcp_tool_factory_interface import (
    McpToolFactoryInterface,
)
from engineering_influence.services.mcp_tool import McpTool


class McpToolFactory(McpToolFactoryInterface):
    """Every tool that can be offered under a valid name is made; the rest are left out.

    Making a tool does not offer it. A stage is offered a tool only if the lock grants it, so a
    server's whole list can be registered while each stage sees none, or only some, of it.
    """

    def create(self, connection: McpConnectionInterface) -> tuple[ToolInterface, ...]:
        """One tool per offerable tool the server advertised, in name order."""
        server = connection.server()
        found = sorted(connection.tools().tools, key=lambda tool: tool.name)
        return tuple(McpTool(connection, tool) for tool in found if tool.offerable(server))
