# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for DoctorCli."""

import argparse
from abc import ABC, abstractmethod


class DoctorCliInterface(ABC):
    """The ``doctor`` command: check that this installation is ready to run."""

    __slots__ = ()

    @abstractmethod
    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``doctor`` to the command line."""

    @abstractmethod
    def run(self, arguments: argparse.Namespace) -> int:
        """Run the checks and return the exit status."""
