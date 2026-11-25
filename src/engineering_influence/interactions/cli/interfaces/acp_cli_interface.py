# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for AcpCli."""

import argparse
from abc import ABC, abstractmethod


class AcpCliInterface(ABC):
    """The ``acp`` command: serve the Agent Client Protocol on stdin and stdout."""

    __slots__ = ()

    @abstractmethod
    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``acp`` to the command line."""

    @abstractmethod
    def run(self, arguments: argparse.Namespace) -> int:
        """Serve until the input ends and return the process status."""
