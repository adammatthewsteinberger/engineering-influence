# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: starting a conversation with an MCP server."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface


class McpTransportFactoryInterface(ABC):
    """Starts a server and returns the transport that talks to it."""

    __slots__ = ()

    @abstractmethod
    def open(self, command: tuple[str, ...], env_names: tuple[str, ...]) -> McpTransportInterface:
        """Start the server with only the named environment variables, and return its transport.

        Raise ``ApplicationError`` when it cannot be started. Closing the transport stops the server.
        """
