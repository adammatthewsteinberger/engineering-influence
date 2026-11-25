# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SkillsCli."""

import argparse
from abc import ABC, abstractmethod


class SkillsCliInterface(ABC):
    """The ``skills`` command: install, enable, list and check prompt skills."""

    __slots__ = ()

    @abstractmethod
    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add the ``skills`` subcommands to the command line."""

    @abstractmethod
    def run(self, arguments: argparse.Namespace) -> int:
        """Run the chosen subcommand and return the exit status."""
