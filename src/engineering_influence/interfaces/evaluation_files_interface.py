# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: reading the files an evaluation is made from."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.evaluation_case import EvaluationCase
    from engineering_influence.models.rubric import Rubric


class EvaluationFilesInterface(ABC):
    """The rubric, the set of books and the baseline, each read strictly."""

    __slots__ = ()

    @abstractmethod
    def rubric(self, path: Path) -> Rubric:
        """The rubric in the TOML file, or an ApplicationError (EVALUATION_FILE_INVALID) that says what is wrong."""

    @abstractmethod
    def cases(self, path: Path) -> tuple[EvaluationCase, ...]:
        """The set of books in the TOML file, in its order."""

    @abstractmethod
    def baseline(self, path: Path) -> dict[str, float]:
        """The dimension means of an earlier evaluation report."""
