# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: reading a file a person gives a run."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.run_input import RunInput


class RunInputReaderInterface(ABC):
    """Turns a text file into a run input, refusing anything that is not plain text."""

    __slots__ = ()

    @abstractmethod
    def read(self, path: Path, name: str | None) -> RunInput:
        """The input, or an ApplicationError (RUN_INPUT_INVALID) saying why the file cannot be one."""
