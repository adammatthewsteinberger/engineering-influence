# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for BookJudge."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_score import BookScore
    from engineering_influence.models.made_book import MadeBook


class BookJudgeInterface(ABC):
    """Scores a finished book against the rubric with a model."""

    __slots__ = ()

    @abstractmethod
    def judge(self, book: MadeBook) -> BookScore:
        """The book's score on every dimension that applies to its kind, and what judging it cost."""
