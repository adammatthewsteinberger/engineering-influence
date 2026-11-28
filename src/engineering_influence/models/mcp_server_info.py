# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Who an MCP server says it is."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.mcp_server_info_interface import (
    McpServerInfoInterface,
)


@dataclass(frozen=True, slots=True)
class McpServerInfo(McpServerInfoInterface):
    """The name and version a server reported when it was initialized, and the protocol agreed.

    The server chose these words, so they are untrusted text: they are compared with what was
    locked, never believed on their own.
    """

    name: str
    version: str
    protocol_version: str

    def __post_init__(self) -> None:
        """Validate the server's reported name, version and protocol when it is built."""
        for label, value in (
            ("name", self.name),
            ("version", self.version),
            ("protocol version", self.protocol_version),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"a server reports its {label}")
