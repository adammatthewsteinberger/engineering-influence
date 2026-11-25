# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for FailureClassifier."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.failure_kind import FailureKind


class FailureClassifierInterface(ABC):
    """Decide what a failed stage should do next."""

    __slots__ = ()

    @abstractmethod
    def classify(self, error: BaseException) -> FailureKind:
        """Retry, park for credit, or stop."""
