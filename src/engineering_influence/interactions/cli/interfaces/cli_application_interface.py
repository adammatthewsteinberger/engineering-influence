# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The command-line application: parse arguments, run a command, return a status."""

from abc import ABC, abstractmethod


class CliApplicationInterface(ABC):
    """What a process entry point needs from the CLI."""

    __slots__ = ()

    @abstractmethod
    def run(self, argv: list[str] | None = None) -> int:
        """Parse the command line and return its process status."""
