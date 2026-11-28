# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for the parts of the home directory a sandboxed server may still read."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class SandboxAllowanceInterface(ABC):
    """Which directories under the home directory a server needs in order to start."""

    __slots__ = ()

    @abstractmethod
    def paths(self, command: tuple[str, ...], home: Path) -> tuple[Path, ...]:
        """The directories strictly below ``home`` that the command reads, in name order."""
