# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for the assets that ship with the package."""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from pathlib import Path


class PackageAssetsInterface(ABC):
    """Locate the class files, stylesheets and fonts as a real directory."""

    __slots__ = ()

    @abstractmethod
    def directory(self) -> AbstractContextManager[Path]:
        """A context manager yielding the assets directory."""
