# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for the native sandbox that an MCP server's process is started inside."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class McpServerSandboxInterface(ABC):
    """Confines one server's process to its own working directory and to no network."""

    __slots__ = ()

    @abstractmethod
    def wrap(self, command: tuple[str, ...], workdir: Path) -> tuple[str, ...]:
        """The command, wrapped so it runs confined. Raise ``ApplicationError`` when no sandbox can be used."""
