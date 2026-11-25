# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: reaching a remote MCP server."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface


class McpRemoteTransportFactoryInterface(ABC):
    """Opens a conversation with a server at an address and returns the transport that carries it."""

    __slots__ = ()

    @abstractmethod
    def open(self, url: str, bearer_env: str) -> McpTransportInterface:
        """Prepare to talk to the server at ``url``; ``bearer_env`` names the variable that holds its token, or is empty.

        Raise ``ApplicationError`` when the address or the credential cannot be used. Closing the
        transport ends the session.
        """
