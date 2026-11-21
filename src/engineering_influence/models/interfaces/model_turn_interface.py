# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ModelTurn."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.tool_result import ToolResult


class ModelTurnInterface(ABC):
    """An assistant turn that called tools, with every result."""

    __slots__ = ()

    @abstractmethod
    def result_for(self, call_id: str) -> ToolResult:
        """The result that answers the call with this id."""
