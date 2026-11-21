# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ProcessMeter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ProcessMeterInterface(ABC):
    """Reads how much memory a process group and how much disk a directory is using."""

    __slots__ = ()

    @abstractmethod
    def memory_bytes(self, group: int) -> int:
        """Resident memory of every process in the group, in bytes; 0 when none is left."""

    @abstractmethod
    def disk_bytes(self, directory: Path) -> int:
        """Total size of the files under the directory, in bytes; 0 when it does not exist."""
