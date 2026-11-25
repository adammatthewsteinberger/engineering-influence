# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for starting a long-running server process from its target name."""

from abc import ABC, abstractmethod


class ServeStarterInterface(ABC):
    """Load settings and run ``api`` or ``worker``; raise on bad configuration."""

    __slots__ = ()

    @abstractmethod
    def start(self, target: str) -> None:
        """Run the chosen process until it stops."""
