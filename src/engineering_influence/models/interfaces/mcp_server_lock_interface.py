# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for McpServerLock."""

from abc import ABC, abstractmethod


class McpServerLockInterface(ABC):
    """One MCP server that has been reviewed and pinned."""

    __slots__ = ()

    @abstractmethod
    def file_hashes(self) -> dict[str, str]:
        """The locked files and their SHA-256, by path."""

    @abstractmethod
    def granted(self, stage: str) -> tuple[str, ...]:
        """The server's own names of the tools this stage may call; none if it has no grant."""

    @abstractmethod
    def model_names(self, stage: str) -> tuple[str, ...]:
        """The names the model sees for the tools this stage may call, ``<server>__<tool>``."""

    @abstractmethod
    def with_grants(self, stage: str, tools: tuple[str, ...]) -> "McpServerLockInterface":
        """This lock with the tools added to what the stage may call; the model checks the result."""

    @abstractmethod
    def without_grants(self, stage: str, tools: tuple[str, ...]) -> "McpServerLockInterface":
        """This lock with the tools taken from what the stage may call; none given takes them all."""
