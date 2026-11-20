# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for listing the files a release must produce."""

from abc import ABC, abstractmethod
from typing import Any


class ArtifactInventoryInterface(ABC):
    """List the required artifacts of a book with their sizes and hashes."""

    __slots__ = ()

    @abstractmethod
    def artifacts(self, slug: str, *, hardcover: bool = False) -> list[dict[str, Any]]:
        """The required artifacts, each with existence, size and hash."""

    @abstractmethod
    def problems(self, artifacts: list[dict[str, Any]]) -> list[str]:
        """A problem for each artifact that does not exist."""
