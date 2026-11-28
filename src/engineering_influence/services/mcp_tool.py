# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One tool of a locked MCP server, as the tool runner sees it."""

from collections.abc import Mapping
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.mcp_tool_descriptor import McpToolDescriptor
from engineering_influence.models.tool_definition import ToolDefinition
from engineering_influence.services.interfaces.mcp_connection_interface import (
    McpConnectionInterface,
)


class McpTool(ToolInterface):
    """The server's description, schema and answer, run through the runner's checks like any tool.

    Its definition is what the server advertised, which matched the lock (so it is the text a person
    reviewed). An answer the server marks as an error becomes an ``ApplicationError``, so the model
    reads it as a failed call it may work around, wrapped as untrusted text like every tool result.
    The ``revision`` is the hash of the server's tools: a server that is updated and locked again
    does not have its old answers replayed for a resumed run.
    """

    def __init__(self, connection: McpConnectionInterface, tool: McpToolDescriptor) -> None:
        """Remember the connection to the server and the tool's descriptor."""
        self._connection = connection
        self._tool = tool
        self._revision = connection.tools().digest()

    def definition(self) -> ToolDefinition:
        """What the model is told about this tool."""
        return self._tool.definition(self._connection.server())

    def revision(self) -> str:
        """The hash of the tools the server advertised."""
        return self._revision

    def invoke(self, arguments: Mapping[str, Any]) -> str:
        """Call the server's tool and return its text."""
        result = self._connection.call(self._tool.name, arguments)
        if result.is_error:
            raise ApplicationError(
                code="MCP_TOOL_ERROR",
                message=result.text or "the tool reported an error and said nothing",
                http_status=502,
            )
        return result.text
