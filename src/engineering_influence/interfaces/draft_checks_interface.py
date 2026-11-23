# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Draft checks port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.quality_issue import QualityIssue


class DraftChecksInterface(ABC):
    """What a kind of book checks across the whole draft, once every chapter is written."""

    __slots__ = ()

    @abstractmethod
    def issues(
        self, texts: Mapping[str, str], chapters: tuple[str, ...]
    ) -> tuple[QualityIssue, ...]:
        """The defects found, none of them blocking; ``chapters`` are numbered from 1 in order."""
