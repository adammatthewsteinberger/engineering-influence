# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PackageBook."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class PackageBookInterface(ABC):
    """Packages one book's finished files and listing into a release bundle."""

    __slots__ = ()

    @abstractmethod
    def package(self, slug: str, config: Mapping[str, Any], release_status: str) -> str:
        """Write the bundle and return a one-line summary; refuse a book that is not ready."""
