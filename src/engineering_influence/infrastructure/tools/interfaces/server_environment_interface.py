# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ServerEnvironment."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ServerEnvironmentInterface(ABC):
    """The environment an MCP server is started with."""

    __slots__ = ()

    @abstractmethod
    def build(self, names: tuple[str, ...], workdir: Path) -> dict[str, str]:
        """The allow-listed variables, the confined ones and the named ones, as a new dict."""
