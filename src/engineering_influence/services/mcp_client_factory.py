# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Makes MCP clients that all introduce themselves the same way."""

from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.services.interfaces.mcp_client_factory_interface import (
    McpClientFactoryInterface,
)
from engineering_influence.services.interfaces.mcp_client_interface import McpClientInterface
from engineering_influence.services.mcp_client import McpClient


class McpClientFactory(McpClientFactoryInterface):
    """Holds the name, version and request timeout every client is made with."""

    def __init__(
        self, client_name: str, client_version: str, timeout_seconds: float = 30.0
    ) -> None:
        """Remember the client name, version and request time limit every client is made with."""
        self._name = client_name
        self._version = client_version
        self._timeout = timeout_seconds

    def create(self, transport: McpTransportInterface) -> McpClientInterface:
        """A client that talks to the server behind this transport."""
        return McpClient(transport, self._name, self._version, self._timeout)
