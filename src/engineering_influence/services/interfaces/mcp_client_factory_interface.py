# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpClientFactory."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
    from engineering_influence.services.interfaces.mcp_client_interface import McpClientInterface


class McpClientFactoryInterface(ABC):
    """Makes an MCP client for a transport."""

    __slots__ = ()

    @abstractmethod
    def create(self, transport: McpTransportInterface) -> McpClientInterface:
        """A client that talks to the server behind this transport."""
