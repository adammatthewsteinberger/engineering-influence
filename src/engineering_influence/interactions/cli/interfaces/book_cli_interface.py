# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``book`` command group."""

import argparse
from abc import ABC, abstractmethod


class BookCliInterface(ABC):
    """Register ``ei book`` and run its subcommands."""

    __slots__ = ()

    @abstractmethod
    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``book`` and its subcommands."""

    @abstractmethod
    def run(self, arguments: argparse.Namespace) -> int:
        """Run the chosen subcommand and return its exit status."""
