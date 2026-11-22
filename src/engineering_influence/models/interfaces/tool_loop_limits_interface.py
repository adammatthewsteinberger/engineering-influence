# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolLoopLimits."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ToolLoopLimitsInterface(ABC):
    """Caps on one tool loop."""

    __slots__ = ()

    @abstractmethod
    def room_for(self, made: int, asking: int) -> bool:
        """True when ``asking`` more calls still fit under the cap after ``made`` calls."""
