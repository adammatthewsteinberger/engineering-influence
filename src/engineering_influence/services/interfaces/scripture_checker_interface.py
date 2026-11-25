# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ScriptureChecker."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.quality_issue import QualityIssue


class ScriptureCheckerInterface(ABC):
    """Checks a chapter's quotations of Scripture against the verses they cite."""

    __slots__ = ()

    @abstractmethod
    def check(self, chapter: int, text: str) -> tuple[QualityIssue, ...]:
        """The findings for the chapter's quotations, as non-blocking issues; none when every quotation is right."""
