# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: the tools that exist, found by name."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.interfaces.tool_interface import ToolInterface
    from engineering_influence.models.tool_definition import ToolDefinition


class ToolRegistryInterface(ABC):
    """Every tool the process has, by name. A stage is given only the ones it names."""

    __slots__ = ()

    @abstractmethod
    def lookup(self, name: str) -> ToolInterface | None:
        """The tool with this name, or None."""

    @abstractmethod
    def definitions(self, names: Sequence[str]) -> tuple[ToolDefinition, ...]:
        """The definitions of the named tools, in that order; a ValueError if any name is unknown."""
