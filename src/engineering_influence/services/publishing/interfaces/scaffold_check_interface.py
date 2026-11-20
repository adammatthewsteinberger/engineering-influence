# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScaffoldCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from engineering_influence.services.publishing.issue_recorder import IssueRecorder


class ScaffoldCheckInterface(ABC):
    """Planning or proof language that leaked into the printed copy."""

    __slots__ = ()

    @abstractmethod
    def run(
        self, recorder: IssueRecorder, path: Path, text: str, body: str, quality: dict[str, Any]
    ) -> None:
        """Record every configured forbidden start and phrase found."""
