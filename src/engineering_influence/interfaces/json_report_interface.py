# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for writing evidence reports."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class JsonReportInterface(ABC):
    """Write a report as JSON."""

    __slots__ = ()

    @abstractmethod
    def write(self, path: Path, data: dict[str, Any], *, ensure_ascii: bool = False) -> None:
        """Write data to path, creating parent directories."""
