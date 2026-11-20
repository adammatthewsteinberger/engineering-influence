# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for reading the repository state."""

from abc import ABC, abstractmethod
from typing import Any


class GitStateInterface(ABC):
    """Report where the repository stood when a release was built."""

    __slots__ = ()

    @abstractmethod
    def read(self) -> dict[str, Any]:
        """Commit, branch and status; None for each when git is unavailable."""
