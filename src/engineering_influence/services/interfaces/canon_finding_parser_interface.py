# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for CanonFindingParser."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.canon_finding import CanonFinding


class CanonFindingParserInterface(ABC):
    """Reads the findings out of a canon check's output."""

    __slots__ = ()

    @abstractmethod
    def parse(self, output: str) -> tuple[CanonFinding, ...]:
        """Every line that reads `ERROR where: [rule] message` or `WARN where: [rule] message`, in order. Other lines are
        the check's own chatter and are ignored."""
