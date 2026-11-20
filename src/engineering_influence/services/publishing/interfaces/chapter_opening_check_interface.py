# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ChapterOpeningCheck."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from engineering_influence.services.publishing.issue_recorder import IssueRecorder


class ChapterOpeningCheckInterface(ABC):
    """A lowercase first paragraph breaks the print initial; later ones are fragments."""

    __slots__ = ()

    @abstractmethod
    def run(
        self, recorder: IssueRecorder, path: Path, text: str, body: str, quality: dict[str, Any]
    ) -> None:
        """Record opening and paragraph-start issues for one chapter."""
