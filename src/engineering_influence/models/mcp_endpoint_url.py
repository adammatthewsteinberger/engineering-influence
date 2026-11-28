# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The address of a remote MCP server."""

from dataclasses import dataclass
from typing import ClassVar
from urllib.parse import urlsplit

from engineering_influence.models.interfaces.mcp_endpoint_url_interface import (
    McpEndpointUrlInterface,
)


@dataclass(frozen=True, slots=True)
class McpEndpointUrl(McpEndpointUrlInterface):
    """An ``https`` address checked before anything is contacted, written the way it is locked.

    It names a host and a path and nothing that could carry a secret: **no user or password, no
    query string and no fragment**, because the lock is a file that gets committed. A credential for
    the server is a named environment variable (the lock's ``bearer_env``), never part of the
    address. Only printable ASCII without spaces is accepted, so what is stored is what is shown.

    Whether the host is somewhere a run may go (a public address, not the machine's own network) is
    not decided here: the URL policy decides that each time a connection is made, because the answer
    depends on DNS, which changes.
    """

    MAX_LENGTH: ClassVar[int] = 2048

    url: str

    def __post_init__(self) -> None:
        """Refuse an address that is not https, before anything is contacted."""
        if not isinstance(self.url, str):
            raise TypeError("a server's address is text")
        if not self.url or len(self.url) > self.MAX_LENGTH:
            raise ValueError(f"a server's address is 1 to {self.MAX_LENGTH} characters")
        if any(not 0x21 <= ord(char) <= 0x7E for char in self.url):
            raise ValueError("a server's address is printable ASCII, with no spaces")
        parts = urlsplit(self.url)
        if parts.scheme != "https":
            raise ValueError("a remote server is reached over https, never plain http")
        if not parts.hostname:
            raise ValueError("a server's address names a host")
        if "@" in parts.netloc:
            raise ValueError("a server's address has no user or password: name a bearer variable")
        if "?" in self.url or "#" in self.url:
            raise ValueError(
                "a server's address has no query string or fragment, which could carry a secret"
            )
        parts.port  # noqa: B018 - reading it raises ValueError for a port that is not a number

    def host(self) -> str:
        """The host name alone, which is what an error message may show."""
        return urlsplit(self.url).hostname or ""
