# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for DbCli."""

import argparse
from abc import ABC, abstractmethod


class DbCliInterface(ABC):
    """The ``db`` command group: manage the database schema."""

    __slots__ = ()

    @abstractmethod
    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``db upgrade`` to the command line."""

    @abstractmethod
    def run(self, arguments: argparse.Namespace) -> int:
        """Run the chosen ``db`` command and return its exit status."""
