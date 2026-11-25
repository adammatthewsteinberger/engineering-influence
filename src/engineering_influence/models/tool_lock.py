# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The servers a person has approved, as written in the lock file."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.tool_lock_interface import ToolLockInterface
from engineering_influence.models.mcp_server_lock import McpServerLock


@dataclass(frozen=True, slots=True)
class ToolLock(ToolLockInterface):
    """Every locked server, by name. A run starts only the servers listed here.

    The lock file is a contract: its format is versioned, and an entry changes only when a person
    runs ``ei tools add`` and reviews the difference like any other commit.
    """

    VERSION: ClassVar[int] = 1

    servers: tuple[McpServerLock, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.servers, tuple):
            raise TypeError("a tool lock is a tuple of servers")
        names = [server.name for server in self.servers]
        if len(set(names)) != len(names):
            raise ValueError("two locked servers share a name")

    def server(self, name: str) -> McpServerLock | None:
        """The locked server with this name, or None."""
        for server in self.servers:
            if server.name == name:
                return server
        return None

    def with_server(self, server: McpServerLock, replace: bool) -> "ToolLock":
        """This lock with the server added; an existing one of that name is replaced only if asked."""
        kept = tuple(existing for existing in self.servers if existing.name != server.name)
        if len(kept) != len(self.servers) and not replace:
            raise ValueError(f"a server named {server.name!r} is already locked")
        return ToolLock((*kept, server))

    def granted(self, stage: str) -> tuple[str, ...]:
        """The model names of every locked tool this stage may call, servers in name order."""
        servers = sorted(self.servers, key=lambda server: server.name)
        return tuple(name for server in servers for name in server.model_names(stage))

    def names(self) -> tuple[str, ...]:
        """The locked servers' names, sorted."""
        return tuple(sorted(server.name for server in self.servers))
