# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ToolsCli."""

import argparse
from abc import ABC, abstractmethod


class ToolsCliInterface(ABC):
    """The ``tools`` command: lock, list and check third-party tool servers."""

    __slots__ = ()

    @abstractmethod
    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``tools add``, ``tools list`` and ``tools verify`` to the command line."""

    @abstractmethod
    def run(self, arguments: argparse.Namespace) -> int:
        """Run the chosen subcommand and return the exit status."""
