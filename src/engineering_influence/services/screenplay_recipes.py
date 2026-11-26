# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The stages of a screenplay run, in order, and the recipe for each: the brief, then the Phase 8 architecture."""

from typing import ClassVar

from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_recipe import StageRecipe


class ScreenplayRecipes(StageRecipesInterface):
    """Each stage is one prompt. Each stage's answer is checked by `ScreenplayOutputChecks` before it is stored, so a
    beat sheet with a missing beat stops the run where it was written. The drafting and the production layer come in
    later stages; until then a screenplay run's plan ends at the scene cards.
    """

    RECIPES: ClassVar[tuple[StageRecipe, ...]] = (
        StageRecipe("brief", "screenplay_brief", (), 1_500),
        StageRecipe("anchors", "screenplay_anchors", ("brief",), 4_000),
        StageRecipe("beats", "screenplay_beats", ("brief", "anchors"), 3_000),
        StageRecipe("scene_cards", "screenplay_scene_cards", ("brief", "anchors", "beats"), 8_192),
    )

    def plan(self) -> StagePlan:
        """The stages of a screenplay run, in order."""
        return StagePlan(BookKind.SCREENPLAY, tuple(recipe.stage for recipe in self.RECIPES))

    def recipe(self, stage: str) -> StageRecipe:
        """The recipe for the stage, or a ValueError when a screenplay run has none for it."""
        for recipe in self.RECIPES:
            if recipe.stage == stage:
                return recipe
        raise ValueError(f"a screenplay run has no recipe for stage {stage!r}")
