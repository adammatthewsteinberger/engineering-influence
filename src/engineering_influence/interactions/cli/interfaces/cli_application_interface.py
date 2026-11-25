# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The command-line application: parse arguments, run a command, return a status."""

import argparse
from abc import ABC, abstractmethod


class CliApplicationInterface(ABC):
    """What a process entry point needs from the CLI."""

    __slots__ = ()

    @abstractmethod
    def parser(self) -> argparse.ArgumentParser:
        """The whole command tree as a parser: every command, option and choice of ``ei``."""

    @abstractmethod
    def run(self, argv: list[str] | None = None) -> int:
        """Parse the command line and return its process status."""
