# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolResult."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.tool_result import ToolResult


class ToolResultInterface(ABC):
    """What a tool gave back for one call."""

    __slots__ = ()

    @abstractmethod
    def capped(self, limit: int) -> ToolResult:
        """The same result with at most ``limit`` characters of content, and a note of what was cut."""
