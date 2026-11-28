# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One running, verified MCP server, shared by every tool that belongs to it."""

import threading
from collections.abc import Mapping
from typing import Any

from engineering_influence.models.mcp_call_result import McpCallResult
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.services.interfaces.mcp_client_interface import McpClientInterface
from engineering_influence.services.interfaces.mcp_connection_interface import (
    McpConnectionInterface,
)


class McpConnection(McpConnectionInterface):
    """Serializes calls, because one server speaks one conversation.

    The tool runner calls tools from several threads, and a client matches answers to requests by
    id on a single stream, so two calls at once would read each other's answers. A call waits for
    the one before it. ``close`` does not wait: it stops the server at once, and a call in flight
    then fails.
    """

    def __init__(self, server: str, client: McpClientInterface, tools: McpToolSet) -> None:
        """Remember the server name, its client and its tools."""
        self._server = server
        self._client = client
        self._tools = tools
        self._one_at_a_time = threading.Lock()

    def server(self) -> str:
        """The server's name in the lock."""
        return self._server

    def tools(self) -> McpToolSet:
        """Every tool the server advertised, which matched the lock when it was started."""
        return self._tools

    def call(self, name: str, arguments: Mapping[str, Any]) -> McpCallResult:
        """Call one of the server's tools; one call at a time."""
        with self._one_at_a_time:
            return self._client.call_tool(name, arguments)

    def close(self) -> None:
        """Stop the server."""
        self._client.close()
