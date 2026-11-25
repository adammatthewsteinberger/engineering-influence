# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BriefReader."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_brief import BookBrief


class BriefReaderInterface(ABC):
    """Reads a brief written as TOML and checks it against the brief contract."""

    __slots__ = ()

    @abstractmethod
    def read_text(self, text: str, source: str) -> BookBrief:
        """The brief, or an ApplicationError (BRIEF_INVALID) that names ``source`` and what is wrong."""
