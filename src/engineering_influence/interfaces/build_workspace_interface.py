# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for the files a book build writes."""

from abc import ABC, abstractmethod
from pathlib import Path


class BuildWorkspaceInterface(ABC):
    """Prepare a build directory, write the LaTeX source, and deliver the finished PDF."""

    __slots__ = ()

    @abstractmethod
    def prepare(self, workdir: Path, assets: Path, hardcover: bool) -> None:
        """Create the directory and copy the class files and fonts into it."""

    @abstractmethod
    def write_text(self, path: Path, text: str) -> None:
        """Write UTF-8 text."""

    @abstractmethod
    def deliver(self, built: Path, destination: Path) -> None:
        """Copy the built file to its destination, creating the destination's folder."""
