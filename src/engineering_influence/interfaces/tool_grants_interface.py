# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: which tools beyond its recipe's own a stage has been granted."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ToolGrantsInterface(ABC):
    """Names the tools a stage may call that its recipe does not list."""

    __slots__ = ()

    @abstractmethod
    def for_stage(self, stage: str) -> tuple[str, ...]:
        """The model names of the tools granted to the stage; none when it has no grant."""
