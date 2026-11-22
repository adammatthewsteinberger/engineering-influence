# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The stages a non-fiction run can do so far, and the recipe for each."""

from typing import ClassVar

from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_recipe import StageRecipe


class NonfictionRecipes(StageRecipesInterface):
    """Brief, positioning, research and outline are one prompt each; ``draft`` follows them with its own executor.

    Research is the one stage with tools (search and page reading); the others have none. ``draft`` has no
    recipe because it is not one prompt: it loops over the chapters (see ``DraftStageExecutor``), so it is
    named in the plan and routed to its own executor. The later stages (revision, copy edit, front and back
    matter, assembly) are added as each one is built, and the plan grows with them.
    """

    DRAFT_STAGE = "draft"

    RECIPES: ClassVar[tuple[StageRecipe, ...]] = (
        StageRecipe("brief", "stage_brief", (), 1_500),
        StageRecipe("positioning", "stage_positioning", ("brief",), 2_000),
        StageRecipe(
            "research",
            "stage_research",
            ("brief", "positioning"),
            4_000,
            ("web_search", "fetch_url"),
        ),
        StageRecipe("outline", "stage_outline", ("brief", "positioning", "research"), 4_000),
    )

    def plan(self) -> StagePlan:
        """The stages of a non-fiction run, in order."""
        stages = (*(recipe.stage for recipe in self.RECIPES), self.DRAFT_STAGE)
        return StagePlan(BookKind.NONFICTION, stages)

    def recipe(self, stage: str) -> StageRecipe:
        """The recipe for the stage, or a ValueError when a non-fiction run has none for it."""
        for recipe in self.RECIPES:
            if recipe.stage == stage:
                return recipe
        raise ValueError(f"a non-fiction run has no recipe for stage {stage!r}")
