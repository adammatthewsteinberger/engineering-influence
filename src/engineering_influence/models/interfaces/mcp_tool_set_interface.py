# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpToolSet."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.tool_definition import ToolDefinition


class McpToolSetInterface(ABC):
    """Everything an MCP server advertised, and the hash that pins it."""

    __slots__ = ()

    @abstractmethod
    def digest(self) -> str:
        """The SHA-256 of the canonical form of every tool, in name order."""

    @abstractmethod
    def names(self) -> tuple[str, ...]:
        """The tool names, sorted."""

    @abstractmethod
    def offered(self, server: str) -> tuple[ToolDefinition, ...]:
        """The definitions that can be given to a model, in name order."""

    @abstractmethod
    def skipped(self, server: str) -> tuple[str, ...]:
        """The names of the tools that cannot be offered, sorted."""
