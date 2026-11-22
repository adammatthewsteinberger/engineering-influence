# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolLoopResult."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ToolLoopResultInterface(ABC):
    """What a tool loop gave back."""

    __slots__ = ()

    @abstractmethod
    def used_tools(self) -> bool:
        """True when at least one tool was called."""
