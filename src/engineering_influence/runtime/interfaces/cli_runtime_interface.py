# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Composition root for the command line."""

from abc import ABC, abstractmethod

from engineering_influence.interactions.cli.interfaces.cli_application_interface import (
    CliApplicationInterface,
)


class CliRuntimeInterface(ABC):
    """Build the fully wired CLI application."""

    __slots__ = ()

    @abstractmethod
    def build(self) -> CliApplicationInterface:
        """Wire the controller, the book commands and the server commands."""
