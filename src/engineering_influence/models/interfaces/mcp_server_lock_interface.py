# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpServerLock."""

from abc import ABC, abstractmethod


class McpServerLockInterface(ABC):
    """One MCP server that has been reviewed and pinned."""

    __slots__ = ()

    @abstractmethod
    def file_hashes(self) -> dict[str, str]:
        """The locked files and their SHA-256, by path."""
