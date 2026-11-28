# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpServerLauncher."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.mcp_server_lock import McpServerLock
    from engineering_influence.services.interfaces.mcp_connection_interface import (
        McpConnectionInterface,
    )


class McpServerLauncherInterface(ABC):
    """Starts a locked server for a run, or refuses."""

    __slots__ = ()

    @abstractmethod
    def verify_files(self, entry: McpServerLock) -> None:
        """Check the files the server would run against the lock, without starting anything.

        Raise ``ApplicationError`` if any file differs from the lock.
        """

    @abstractmethod
    def start(self, entry: McpServerLock) -> McpConnectionInterface:
        """Check the files, start the server, check what it says, and return the connection.

        Raise ``ApplicationError`` (never a half-started server) if anything differs from the lock.
        """
