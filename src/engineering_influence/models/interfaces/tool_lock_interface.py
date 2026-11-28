# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolLock."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.mcp_server_lock import McpServerLock
    from engineering_influence.models.tool_lock import ToolLock


class ToolLockInterface(ABC):
    """The servers a person has approved, as written in the lock file."""

    __slots__ = ()

    @abstractmethod
    def server(self, name: str) -> McpServerLock | None:
        """The locked server with this name, or None."""

    @abstractmethod
    def with_server(self, server: McpServerLock, replace: bool) -> ToolLock:
        """This lock with the server added; an existing one of that name is replaced only if asked."""

    @abstractmethod
    def granted(self, stage: str, servers: tuple[str, ...] | None = None) -> tuple[str, ...]:
        """The model names of every locked tool this stage may call, servers in name order.

        ``servers`` restricts the answer to the named servers; ``None`` means every locked server.
        """

    @abstractmethod
    def names(self) -> tuple[str, ...]:
        """The locked servers' names, sorted."""
