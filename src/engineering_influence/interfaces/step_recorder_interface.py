# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for running a pipeline step and recording evidence."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any


class StepRecorderInterface(ABC):
    """Run one step and log what happened."""

    __slots__ = ()

    @abstractmethod
    def run(
        self, name: str, command: list[str], action: Callable[[], str], log_path: Path
    ) -> dict[str, Any]:
        """Run the action, write its output to log_path, and return the record."""
