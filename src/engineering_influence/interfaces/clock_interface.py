# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for the current time."""

from abc import ABC, abstractmethod
from datetime import datetime


class ClockInterface(ABC):
    """Tell the time, so nothing else reads the system clock."""

    __slots__ = ()

    @abstractmethod
    def now(self) -> datetime:
        """The current moment, timezone-aware."""
