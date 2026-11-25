# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for StageRecipe."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection


class StageRecipeInterface(ABC):
    """What one stage reads, which prompt it uses and how much it may write."""

    __slots__ = ()

    @abstractmethod
    def output_name(self) -> str:
        """The artifact this stage's answer is kept as."""

    @abstractmethod
    def input_artifacts(self) -> dict[str, str]:
        """Each input's blank name, and the artifact it is read from."""

    @abstractmethod
    def missing(self, stored: Collection[str]) -> tuple[str, ...]:
        """The input artifacts that are not among the stored ones, in order."""
