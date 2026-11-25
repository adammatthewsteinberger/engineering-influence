# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EvaluateCli."""

import argparse
from abc import ABC, abstractmethod


class EvaluateCliInterface(ABC):
    """The ``evaluate`` command: make the evaluation set into books and score them against the rubric."""

    __slots__ = ()

    @abstractmethod
    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``evaluate`` to the command line."""

    @abstractmethod
    def run(self, arguments: argparse.Namespace) -> int:
        """Run the evaluation and return the process status."""
