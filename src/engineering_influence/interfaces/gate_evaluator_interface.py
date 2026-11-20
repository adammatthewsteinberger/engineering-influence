# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate-evaluation port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.artifact import Artifact


class GateEvaluatorInterface(ABC):
    """Evaluate deterministic or rubric-backed automatic gates."""

    __slots__ = ()

    @abstractmethod
    def evaluate(self, artifact: Artifact) -> bool:
        """Return whether an automatic gate accepts an artifact."""
