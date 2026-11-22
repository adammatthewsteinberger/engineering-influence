# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolLock."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.mcp_server_lock import McpServerLock


class ToolLockInterface(ABC):
    """The servers a person has approved, as written in the lock file."""

    __slots__ = ()

    @abstractmethod
    def server(self, name: str) -> McpServerLock | None:
        """The locked server with this name, or None."""

    @abstractmethod
    def names(self) -> tuple[str, ...]:
        """The locked servers' names, sorted."""
