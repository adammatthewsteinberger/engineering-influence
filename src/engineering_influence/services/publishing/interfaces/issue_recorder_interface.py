# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for IssueRecorder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class IssueRecorderInterface(ABC):
    """Turns a path and a text offset into a root-relative path and a line number."""

    __slots__ = ()

    @abstractmethod
    def record(
        self,
        severity: str,
        code: str,
        message: str,
        path: Path | None = None,
        text: str | None = None,
        offset: int | None = None,
    ) -> None:
        """Add an issue, computing its 1-based line when text and offset are given."""
