# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The stages a non-fiction run can do so far, and the recipe for each."""

from typing import ClassVar

from engineering_influence.interfaces.stage_recipes_interface import StageRecipesInterface
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.models.stage_recipe import StageRecipe


class NonfictionRecipes(StageRecipesInterface):
    """Brief, positioning, research, outline and metadata are one prompt each; the stages after them have their own executors.

    Research is the one stage with tools (search and page reading); the others have none. ``draft`` loops over the
    chapters (see ``DraftStageExecutor``); ``revise_structure``, ``revise_lines`` and ``copy_edit`` are editing
    passes over every chapter (see ``RevisionStageExecutor`` and ``NonfictionRevisionPasses``); ``assemble`` and
    ``audit`` make no model call (see ``AssembleStageExecutor`` and ``AuditStageExecutor``), and nor does ``build``
    (see ``BuildStageExecutor``), which builds the PDF, the EPUB and the covers and packages the KDP bundle. None of
    them has a recipe, because none is one prompt, so all are named in the plan and routed to their own executors.
    """

    DRAFT_STAGE = "draft"
    REVISION_STAGES = ("revise_structure", "revise_lines", "copy_edit")
    ASSEMBLE_STAGE = "assemble"
    AUDIT_STAGE = "audit"
    BUILD_STAGE = "build"

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
        StageRecipe("metadata", "stage_metadata", ("brief", "positioning", "outline"), 2_500),
    )

    def plan(self) -> StagePlan:
        """The stages of a non-fiction run, in order."""
        stages = (
            *(recipe.stage for recipe in self.RECIPES),
            self.DRAFT_STAGE,
            *self.REVISION_STAGES,
            self.ASSEMBLE_STAGE,
            self.AUDIT_STAGE,
            self.BUILD_STAGE,
        )
        return StagePlan(BookKind.NONFICTION, stages)

    def recipe(self, stage: str) -> StageRecipe:
        """The recipe for the stage, or a ValueError when a non-fiction run has none for it."""
        for recipe in self.RECIPES:
            if recipe.stage == stage:
                return recipe
        raise ValueError(f"a non-fiction run has no recipe for stage {stage!r}")
