# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolServerFleet."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.tool_interface import ToolInterface
    from engineering_influence.models.tool_lock import ToolLock


class ToolServerFleetInterface(ABC):
    """Every server in a lock, started for a run and stopped at its end."""

    __slots__ = ()

    @abstractmethod
    def start(self, lock: ToolLock) -> None:
        """Start and verify each server; if any fails, stop the ones already started and raise."""

    @abstractmethod
    def tools(self) -> tuple[ToolInterface, ...]:
        """The tools of every started server."""

    @abstractmethod
    def close(self) -> None:
        """Stop every server that was started. Safe to call twice."""
