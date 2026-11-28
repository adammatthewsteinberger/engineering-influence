# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ServerActivator."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ServerActivatorInterface(ABC):
    """Starts the locked servers a stage needs, before the stage offers their tools."""

    __slots__ = ()

    @abstractmethod
    def activate(self, stage: str, selected: tuple[str, ...] | None) -> None:
        """Start, once each, the locked servers the stage is granted and the run selected.

        ``selected`` of None means every server the lock grants the stage (a command-line run).
        """
