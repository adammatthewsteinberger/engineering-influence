# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for reading manuscript and configuration files."""

from abc import ABC, abstractmethod
from pathlib import Path


class ManuscriptSourceInterface(ABC):
    """The file reads the audits and checks need, kept out of the services."""

    __slots__ = ()

    @abstractmethod
    def exists(self, path: Path) -> bool:
        """Whether the file or directory exists."""

    @abstractmethod
    def read_text(self, path: Path, errors: str = "strict") -> str:
        """Return the file's UTF-8 text; raise OSError when it cannot be read."""

    @abstractmethod
    def markdown_names(self, directory: Path) -> set[str]:
        """The names of the Markdown files directly inside the directory."""
