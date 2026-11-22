# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A server that was just locked, and the lock that now holds it."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.tool_lock_addition_interface import (
    ToolLockAdditionInterface,
)
from engineering_influence.models.mcp_server_inspection import McpServerInspection
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_lock import ToolLock


@dataclass(frozen=True, slots=True)
class ToolLockAddition(ToolLockAdditionInterface):
    """The new lock, the entry that was added to it, and what the server said, for a person to review."""

    lock: ToolLock
    server: McpServerLock
    inspection: McpServerInspection
