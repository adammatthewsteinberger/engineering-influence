# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolDefinition."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ToolDefinitionInterface(ABC):
    """A tool the model may call."""

    __slots__ = ()

    @abstractmethod
    def json_schema(self) -> dict[str, Any]:
        """A copy of the parameter schema, safe to give to an adapter that may reshape it."""
