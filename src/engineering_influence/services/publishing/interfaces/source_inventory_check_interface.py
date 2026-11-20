# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SourceInventoryCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.services.publishing.issue_recorder import IssueRecorder


class SourceInventoryCheckInterface(ABC):
    """Finds unlisted sources and ignore entries that name missing files."""

    __slots__ = ()

    @abstractmethod
    def run(
        self, recorder: IssueRecorder, source: Path, listed: list[str], ignored: list[str]
    ) -> set[str]:
        """Record inventory issues and return the Markdown file names found."""
