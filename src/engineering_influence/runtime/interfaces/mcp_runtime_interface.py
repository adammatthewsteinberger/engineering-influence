# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpRuntime."""

from abc import ABC, abstractmethod
from typing import Any


class McpRuntimeInterface(ABC):
    """Build the MCP server from settings and serve it over stdio."""

    __slots__ = ()

    @abstractmethod
    def build_server(self) -> Any:
        """Wire the ledger, the queue and the run services into an MCP server."""

    @abstractmethod
    def run(self) -> None:
        """Configure logging, build the server, and serve until the host closes the pipe."""

    @abstractmethod
    def close(self) -> None:
        """Dispose of every database pool."""
