# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpEndpointUrl."""

from abc import ABC, abstractmethod


class McpEndpointUrlInterface(ABC):
    """The address of a remote MCP server."""

    __slots__ = ()

    @abstractmethod
    def host(self) -> str:
        """The host name alone, which is what an error message may show."""
