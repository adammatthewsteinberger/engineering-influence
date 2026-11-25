# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolCall."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ToolCallInterface(ABC):
    """One call a model asked for."""

    __slots__ = ()

    @abstractmethod
    def arguments_json(self) -> str:
        """The arguments as one canonical line of JSON: the same call always gives the same text."""
