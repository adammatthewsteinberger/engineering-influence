# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolLockFinding."""

from abc import ABC, abstractmethod


class ToolLockFindingInterface(ABC):
    """The result of checking one locked server."""

    __slots__ = ()

    @abstractmethod
    def passed(self) -> bool:
        """True when nothing differs from what was approved."""

    @abstractmethod
    def lines(self) -> tuple[str, ...]:
        """The lines to print: one ``ok`` line, or one ``FAIL`` line per problem."""
