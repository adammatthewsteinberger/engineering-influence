# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for the set of recipes a kind of book uses."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.stage_plan import StagePlan
    from engineering_influence.models.stage_recipe import StageRecipe


class StageRecipesInterface(ABC):
    """The stages a kind of book can do, and what each one reads and says."""

    __slots__ = ()

    @abstractmethod
    def plan(self) -> StagePlan:
        """The stages of a run, in order."""

    @abstractmethod
    def recipe(self, stage: str) -> StageRecipe:
        """The recipe for the stage, or a ValueError when there is none."""
