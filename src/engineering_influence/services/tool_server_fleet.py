# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Verifies every locked server at boot, and starts each one on first use, once."""

from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.services.interfaces.mcp_connection_interface import (
    McpConnectionInterface,
)
from engineering_influence.services.interfaces.mcp_server_launcher_interface import (
    McpServerLauncherInterface,
)
from engineering_influence.services.interfaces.mcp_tool_factory_interface import (
    McpToolFactoryInterface,
)
from engineering_influence.services.interfaces.tool_server_fleet_interface import (
    ToolServerFleetInterface,
)


class ToolServerFleet(ToolServerFleetInterface):
    """Verifying changes no process; starting runs a server.

    ``verify`` checks each server's files against the lock, so a changed file stops the worker before
    anything runs. ``activate`` starts one server, checks what it says, and returns its tools; a server
    already running returns nothing. A server that cannot be started, or is not what was approved, raises,
    and the servers already running stay running. Closing stops every running server in reverse order, and
    closing again does nothing.
    """

    def __init__(
        self, launcher: McpServerLauncherInterface, factory: McpToolFactoryInterface
    ) -> None:
        """Remember the launcher and the factory the servers are started with."""
        self._launcher = launcher
        self._factory = factory
        self._connections: dict[str, McpConnectionInterface] = {}

    def verify(self, lock: ToolLock) -> None:
        """Check the files of every server in the lock, in name order; start none."""
        for entry in sorted(lock.servers, key=lambda server: server.name):
            self._launcher.verify_files(entry)

    def activate(self, entry: McpServerLock) -> tuple[ToolInterface, ...]:
        """Start the server if it is not running, and return its tools; nothing if it already runs."""
        if entry.name in self._connections:
            return ()
        connection = self._launcher.start(entry)
        try:
            tools = self._factory.create(connection)
        except BaseException:
            connection.close()
            raise
        self._connections[entry.name] = connection
        return tools

    def running(self) -> tuple[str, ...]:
        """The names of the servers running now, in the order they started."""
        return tuple(self._connections)

    def close(self) -> None:
        """Stop every running server. Safe to call twice."""
        connections, self._connections = list(self._connections.values()), {}
        for connection in reversed(connections):
            connection.close()
