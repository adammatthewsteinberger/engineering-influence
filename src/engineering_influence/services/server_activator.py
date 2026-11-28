# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starts, for a stage of a run, the locked servers the run selected and the lock grants the stage."""

from engineering_influence.interfaces.tool_registry_interface import ToolRegistryInterface
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.services.interfaces.server_activator_interface import (
    ServerActivatorInterface,
)
from engineering_influence.services.interfaces.tool_server_fleet_interface import (
    ToolServerFleetInterface,
)


class ServerActivator(ServerActivatorInterface):
    """A server the stage does not need is never started, so an unapproved server is never run.

    A server the stage needs is started at most once for the process. Its tools join the registry
    the moment it starts, and the stage offers them after this returns.
    """

    def __init__(
        self, lock: ToolLock, fleet: ToolServerFleetInterface, tools: ToolRegistryInterface
    ) -> None:
        self._lock = lock
        self._fleet = fleet
        self._tools = tools

    def activate(self, stage: str, selected: tuple[str, ...] | None) -> None:
        for entry in sorted(self._lock.servers, key=lambda server: server.name):
            if selected is not None and entry.name not in selected:
                continue
            if not entry.granted(stage):
                continue
            self._tools.register(self._fleet.activate(entry))
