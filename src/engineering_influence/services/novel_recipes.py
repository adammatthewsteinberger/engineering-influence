# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The stages a novel run can do so far, and the recipe for each."""

from typing import ClassVar

from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_recipe import StageRecipe


class NovelRecipes(StageRecipesInterface):
    """Brief, story bible, beats and chapter outline are one prompt each, none with tools.

    A novel is not argued from sources, so there is no research stage and no tool. The story bible is JSON that
    ``StoryBibleParser`` reads and the chapter outline is the same markdown ``OutlineParser`` reads, so the stages
    after them (drafting, which checks each chapter against the bible) walk the same chapters a non-fiction book has.
    The plan grows as those stages are built.
    """

    RECIPES: ClassVar[tuple[StageRecipe, ...]] = (
        StageRecipe("brief", "novel_brief", (), 1_500),
        StageRecipe("story_bible", "novel_story_bible", ("brief",), 4_000),
        StageRecipe("beats", "novel_beats", ("brief", "story_bible"), 3_000),
        StageRecipe("outline", "novel_outline", ("brief", "story_bible", "beats"), 5_000),
    )

    def plan(self) -> StagePlan:
        """The stages of a novel run, in order."""
        return StagePlan(BookKind.NOVEL, tuple(recipe.stage for recipe in self.RECIPES))

    def recipe(self, stage: str) -> StageRecipe:
        """The recipe for the stage, or a ValueError when a novel run has none for it."""
        for recipe in self.RECIPES:
            if recipe.stage == stage:
                return recipe
        raise ValueError(f"a novel run has no recipe for stage {stage!r}")
