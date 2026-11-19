# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``serve`` command group."""

import argparse
from abc import ABC, abstractmethod


class ServeCliInterface(ABC):
    """Register ``ei serve`` and run the chosen target."""

    __slots__ = ()

    @abstractmethod
    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``serve api`` and ``serve worker``."""

    @abstractmethod
    def run(self, arguments: argparse.Namespace) -> int:
        """Start the chosen process; return its exit status."""
