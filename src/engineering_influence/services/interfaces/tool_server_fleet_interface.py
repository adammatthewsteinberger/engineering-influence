# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolServerFleet."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.tool_interface import ToolInterface
    from engineering_influence.models.mcp_server_lock import McpServerLock
    from engineering_influence.models.tool_lock import ToolLock


class ToolServerFleetInterface(ABC):
    """Every server in a lock: verified at boot, started on first use, stopped at the end."""

    __slots__ = ()

    @abstractmethod
    def verify(self, lock: ToolLock) -> None:
        """Check the files of every server in the lock, starting none; raise if any differs."""

    @abstractmethod
    def activate(self, entry: McpServerLock) -> tuple[ToolInterface, ...]:
        """Start the server if it is not running, and return its tools; nothing if it already runs."""

    @abstractmethod
    def running(self) -> tuple[str, ...]:
        """The names of the servers running now."""

    @abstractmethod
    def close(self) -> None:
        """Stop every running server. Safe to call twice."""
