# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starts all the servers in a tool lock, or none of them."""

from engineering_influence.interfaces.tool_interface import ToolInterface
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
    """Servers start in name order. The first one that cannot be started stops the rest of the start.

    A server that was started is stopped again if a later one fails, so a refused run leaves nothing
    running. Closing stops them in the reverse order, and closing again does nothing.
    """

    def __init__(
        self, launcher: McpServerLauncherInterface, factory: McpToolFactoryInterface
    ) -> None:
        self._launcher = launcher
        self._factory = factory
        self._connections: list[McpConnectionInterface] = []
        self._tools: list[ToolInterface] = []

    def start(self, lock: ToolLock) -> None:
        """Start and verify each server; if any fails, stop the ones already started and raise."""
        try:
            for entry in sorted(lock.servers, key=lambda server: server.name):
                connection = self._launcher.start(entry)
                self._connections.append(connection)
                self._tools.extend(self._factory.create(connection))
        except BaseException:
            self.close()
            raise

    def tools(self) -> tuple[ToolInterface, ...]:
        """The tools of every started server."""
        return tuple(self._tools)

    def close(self) -> None:
        """Stop every server that was started. Safe to call twice."""
        connections, self._connections = self._connections, []
        self._tools = []
        for connection in reversed(connections):
            connection.close()
