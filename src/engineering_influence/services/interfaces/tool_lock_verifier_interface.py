# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolLockVerifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.mcp_server_info import McpServerInfo
    from engineering_influence.models.mcp_server_lock import McpServerLock
    from engineering_influence.models.mcp_tool_set import McpToolSet


class ToolLockVerifierInterface(ABC):
    """Compares a locked server with what is on disk and what the running server says."""

    __slots__ = ()

    @abstractmethod
    def check_files(self, entry: McpServerLock) -> tuple[str, ...]:
        """What is wrong with the files the command would run; empty when they are as locked.

        This needs nothing from the server, so it can be done before the server is started.
        """

    @abstractmethod
    def check_server(
        self, entry: McpServerLock, info: McpServerInfo, tools: McpToolSet
    ) -> tuple[str, ...]:
        """What differs between the lock and what the running server reports; empty when nothing."""

    @abstractmethod
    def check(
        self, entry: McpServerLock, info: McpServerInfo, tools: McpToolSet
    ) -> tuple[str, ...]:
        """The problems with the files and with the server's report, together."""
