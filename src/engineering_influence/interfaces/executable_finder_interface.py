# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: finding the file a command name refers to."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ExecutableFinderInterface(ABC):
    """Turns a command name into the absolute path of an executable file."""

    __slots__ = ()

    @abstractmethod
    def find(self, name: str) -> str | None:
        """The absolute path of the executable ``name`` refers to, or None when there is none."""
