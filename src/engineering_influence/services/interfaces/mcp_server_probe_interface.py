# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpServerProbe."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.mcp_server_inspection import McpServerInspection
    from engineering_influence.models.mcp_server_lock import McpServerLock


class McpServerProbeInterface(ABC):
    """Starts a server, asks it who it is and what it offers, and stops it."""

    __slots__ = ()

    @abstractmethod
    def inspect(self, command: tuple[str, ...], env_names: tuple[str, ...]) -> McpServerInspection:
        """Start the server, ask, stop it, and return what it said."""

    @abstractmethod
    def inspect_remote(self, url: str, bearer_env: str) -> McpServerInspection:
        """Contact the server at the address, ask, end the session, and return what it said."""

    @abstractmethod
    def check(self, entry: McpServerLock) -> tuple[str, ...]:
        """What differs between the lock and the files and the running server; empty when nothing."""
