# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Path guard port."""

from abc import ABC, abstractmethod
from pathlib import Path


class PathGuardPort(ABC):
    """Keep caller-supplied names and paths inside a directory they may not leave."""

    @abstractmethod
    def confine(self, raw: str | Path, root: Path) -> Path:
        """Return the resolved path or raise an ApplicationError when it escapes root."""

    @abstractmethod
    def segment(self, value: str) -> str:
        """Return a single safe path component derived from untrusted text."""
